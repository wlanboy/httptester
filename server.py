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

def clamp_timeout(value: float) -> float:
    return max(MIN_REQUEST_TIMEOUT, min(value, MAX_REQUEST_TIMEOUT))

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

class ResolveIn(BaseModel):
    hostname: str

class ResolveOut(BaseModel):
    result: str

@app.post("/api/resolve", response_model=ResolveOut)
async def resolve_hostname(data: ResolveIn):
    async def work() -> str:
        ip_address = await asyncio.wait_for(
            asyncio.to_thread(socket.gethostbyname, data.hostname), timeout=DNS_TIMEOUT
        )
        return f"Hostname: {data.hostname} IP-Adresse: {ip_address}"

    result = await try_or_message(
        work,
        handlers=[
            (TimeoutError, lambda e: f"Timeout beim Auflösen des Hostnamens '{data.hostname}' nach {DNS_TIMEOUT}s"),
            (socket.gaierror, lambda e: f"Fehler beim Auflösen des Hostnamens '{data.hostname}': {e}"),
        ],
        default=lambda e: f"Ein unerwarteter Fehler ist aufgetreten: {e}",
    )
    return ResolveOut(result=result)

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
