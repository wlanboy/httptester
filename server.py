import asyncio
import logging
import socket
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DNS_TIMEOUT = 5.0
MIN_REQUEST_TIMEOUT = 0.1
MAX_REQUEST_TIMEOUT = 30.0
ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "HEAD", "PATCH", "OPTIONS"}
MAX_REPEAT_COUNT = 20

def clamp_timeout(value: float) -> float:
    return max(MIN_REQUEST_TIMEOUT, min(value, MAX_REQUEST_TIMEOUT))

def clamp_count(value: int) -> int:
    return max(1, min(value, MAX_REPEAT_COUNT))

async def try_or_message[T](
    work: Callable[[], Awaitable[T]],
    *,
    handlers: list[tuple[type[BaseException], Callable[[BaseException], T]]],
    default: Callable[[BaseException], T],
) -> T:
    try:
        return await work()
    except Exception as e:  # noqa: BLE001 - dispatched to caller-supplied handlers below
        for exc_type, formatter in handlers:
            if isinstance(e, exc_type):
                return formatter(e)
        return default(e)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    logger.info("Shutdown event received. Shutting down gracefully...")

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/healthz")
async def healthz():
    return JSONResponse(content={"status": "ok"})

@app.get("/")
async def get_home():
    return FileResponse("static/index.html")

def parse_headers(raw: str) -> dict[str, str]:
    headers = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        headers[key.strip()] = value.strip()
    return headers

class RequestIn(BaseModel):
    url: str
    method: str = "GET"
    timeout: float = 5.0
    headers: str = ""

    @field_validator("timeout", mode="before")
    @classmethod
    def _coerce_timeout(cls, v: object) -> float:
        try:
            return float(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 5.0

class RedirectHop(BaseModel):
    status_code: int
    from_url: str
    location: str

class RequestOut(BaseModel):
    response: str
    headers: dict[str, str] = {}
    redirects: list[RedirectHop] = []

@app.post("/api/request", response_model=RequestOut)
async def post_request(data: RequestIn):
    method = data.method.upper() if data.method.upper() in ALLOWED_METHODS else "GET"
    timeout_value = clamp_timeout(data.timeout)

    async def work() -> tuple[str, dict[str, str], list[RedirectHop]]:
        res = await asyncio.to_thread(
            requests.request, method, data.url, headers=parse_headers(data.headers), timeout=timeout_value
        )
        redirects = [
            RedirectHop(status_code=hop.status_code, from_url=hop.url, location=hop.headers.get("Location", ""))
            for hop in res.history
        ]
        return res.text, dict(res.headers), redirects

    response_text, response_headers, redirects = await try_or_message(
        work,
        handlers=[(requests.exceptions.Timeout, lambda e: (f"Timeout: {e}", {}, []))],
        default=lambda e: (f"Fehler: {e}", {}, []),
    )
    return RequestOut(response=response_text, headers=response_headers, redirects=redirects)

class RepeatIn(BaseModel):
    url: str
    method: str = "GET"
    timeout: float = 5.0
    headers: str = ""
    count: int = 5

    @field_validator("timeout", mode="before")
    @classmethod
    def _coerce_timeout(cls, v: object) -> float:
        try:
            return float(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 5.0

    @field_validator("count", mode="before")
    @classmethod
    def _coerce_count(cls, v: object) -> int:
        try:
            return int(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 5

class RepeatAttempt(BaseModel):
    attempt: int
    status_code: int | None = None
    duration_ms: float | None = None
    error: str | None = None

class RepeatStats(BaseModel):
    count: int
    success_count: int
    min_ms: float | None = None
    avg_ms: float | None = None
    max_ms: float | None = None

class RepeatOut(BaseModel):
    stats: RepeatStats
    attempts: list[RepeatAttempt]

@app.post("/api/repeat", response_model=RepeatOut)
async def repeat_request(data: RepeatIn):
    method = data.method.upper() if data.method.upper() in ALLOWED_METHODS else "GET"
    timeout_value = clamp_timeout(data.timeout)
    count = clamp_count(data.count)
    parsed_headers = parse_headers(data.headers)

    attempts: list[RepeatAttempt] = []
    for i in range(1, count + 1):
        start = time.monotonic()
        try:
            res = await asyncio.to_thread(requests.request, method, data.url, headers=parsed_headers, timeout=timeout_value)
            attempts.append(RepeatAttempt(
                attempt=i,
                status_code=res.status_code,
                duration_ms=round((time.monotonic() - start) * 1000, 1),
            ))
        except requests.exceptions.RequestException as e:
            attempts.append(RepeatAttempt(
                attempt=i,
                duration_ms=round((time.monotonic() - start) * 1000, 1),
                error=str(e),
            ))

    durations = [a.duration_ms for a in attempts if a.duration_ms is not None]
    success_count = sum(1 for a in attempts if a.status_code is not None and a.status_code < 400)
    stats = RepeatStats(
        count=count,
        success_count=success_count,
        min_ms=min(durations) if durations else None,
        avg_ms=round(sum(durations) / len(durations), 1) if durations else None,
        max_ms=max(durations) if durations else None,
    )
    return RepeatOut(stats=stats, attempts=attempts)

class ResolveIn(BaseModel):
    hostname: str

class ResolveOut(BaseModel):
    result: str
    addresses: list[str] = []

@app.post("/api/resolve", response_model=ResolveOut)
async def resolve_hostname(data: ResolveIn):
    async def work() -> tuple[str, list[str]]:
        infos = await asyncio.wait_for(
            asyncio.to_thread(socket.getaddrinfo, data.hostname, None), timeout=DNS_TIMEOUT
        )
        addresses = []
        for _family, _type, _proto, _canonname, sockaddr in infos:
            ip = sockaddr[0]
            if ip not in addresses:
                addresses.append(ip)
        return f"Hostname: {data.hostname} IP-Adressen: {', '.join(addresses)}", addresses

    result, addresses = await try_or_message(
        work,
        handlers=[
            (TimeoutError, lambda e: (f"Timeout beim Auflösen des Hostnamens '{data.hostname}' nach {DNS_TIMEOUT}s", [])),
            (socket.gaierror, lambda e: (f"Fehler beim Auflösen des Hostnamens '{data.hostname}': {e}", [])),
        ],
        default=lambda e: (f"Ein unerwarteter Fehler ist aufgetreten: {e}", []),
    )
    return ResolveOut(result=result, addresses=addresses)

class BodyData(BaseModel):
    message: str
    value: int

@app.post("/postbody")
async def post_body(data: BodyData):
    logger.info(f"Received body: {data}")
    return JSONResponse(content={
        "echo_message": data.message,
        "echo_value": data.value,
        "status": "ok"
    })

MAX_CHAIN_HOPS = 20
CHAIN_TIMEOUT_DEFAULT = 5.0

class ChainHop(BaseModel):
    target: str
    status_code: int | None = None
    duration_ms: float | None = None
    error: str | None = None

class ChainRequest(BaseModel):
    message: str | None = None
    chain: list[str] = []
    timeout: float = CHAIN_TIMEOUT_DEFAULT

class ChainResponse(BaseModel):
    message: str | None = None
    final_status: int
    path: list[ChainHop]

async def _call_next_hop(
    next_url: str, rest: list[str], data: ChainRequest, timeout_value: float
) -> tuple[list[ChainHop], int]:
    hop = ChainHop(target=next_url)
    start = time.monotonic()
    try:
        res = await asyncio.to_thread(
            requests.post,
            f"{next_url.rstrip('/')}/chain",
            json={"message": data.message, "chain": rest, "timeout": timeout_value},
            timeout=timeout_value,
        )
        hop.duration_ms = round((time.monotonic() - start) * 1000, 1)
        hop.status_code = res.status_code
        try:
            downstream = res.json()
            path = [hop] + [ChainHop(**h) for h in downstream.get("path", [])]
            final_status = downstream.get("final_status", res.status_code)
        except ValueError:
            hop.error = "Ungueltige Antwort (kein JSON)"
            path = [hop]
            final_status = 502
    except (requests.exceptions.RequestException, ValueError) as e:
        hop.duration_ms = round((time.monotonic() - start) * 1000, 1)
        hop.error = str(e)
        path = [hop]
        final_status = 502

    return path, final_status

async def run_chain(data: ChainRequest) -> ChainResponse:
    if not data.chain:
        return ChainResponse(message=data.message, final_status=200, path=[])

    if len(data.chain) > MAX_CHAIN_HOPS:
        return ChainResponse(
            message=data.message,
            final_status=400,
            path=[ChainHop(target=data.chain[0], error=f"Kette zu lang (> {MAX_CHAIN_HOPS} Hops), abgebrochen")],
        )

    next_url, *rest = data.chain
    timeout_value = clamp_timeout(data.timeout)
    path, final_status = await _call_next_hop(next_url, rest, data, timeout_value)
    return ChainResponse(message=data.message, final_status=final_status, path=path)

@app.post("/chain", response_model=ChainResponse)
async def chain(data: ChainRequest):
    return await run_chain(data)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
