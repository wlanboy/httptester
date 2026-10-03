import asyncio
import codecs
import logging
import socket
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import requests
import urllib3
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError, field_validator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# verify_tls=false ist eine bewusste Entscheidung des Nutzers, keine Warnung pro Request loggen
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

STATIC_DIR = Path(__file__).resolve().parent / "static"

DNS_TIMEOUT = 5.0
MIN_REQUEST_TIMEOUT = 0.1
MAX_REQUEST_TIMEOUT = 30.0
ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "HEAD", "PATCH", "OPTIONS"}
MAX_REPEAT_COUNT = 20
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_CHAIN_HOPS = 20
CHAIN_TIMEOUT_DEFAULT = 5.0

def clamp_timeout(value: float) -> float:
    return max(MIN_REQUEST_TIMEOUT, min(value, MAX_REQUEST_TIMEOUT))

def clamp_count(value: int) -> int:
    return max(1, min(value, MAX_REPEAT_COUNT))

def elapsed_ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 1)

@dataclass
class Fetched:
    response: requests.Response
    body: bytes
    truncated: bool
    duration_ms: float

def read_limited(res: requests.Response, limit: int) -> tuple[bytes, bool]:
    buf = bytearray()
    for chunk in res.iter_content(chunk_size=64 * 1024):
        buf += chunk
        if len(buf) > limit:
            return bytes(buf[:limit]), True
    return bytes(buf), False

def decode_body(body: bytes, encoding: str | None, *, charset_declared: bool = True, truncated: bool = False) -> str:
    # Ohne charset setzt requests bei text/* ISO-8859-1; die meisten Seiten sind aber UTF-8.
    # Inkrementell dekodieren, damit ein beim Abschneiden halbiertes Zeichen kein Fehler ist.
    if not charset_declared:
        try:
            return codecs.getincrementaldecoder("utf-8")().decode(body, final=not truncated)
        except UnicodeDecodeError:
            pass
    try:
        return body.decode(encoding or "utf-8", errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")

def fetch(method: str, url: str, *, headers: dict[str, str], timeout: float, verify: bool) -> Fetched:
    """Blockierender Request; liest den Body höchstens bis MAX_RESPONSE_BYTES, damit große Downloads den Pod nicht sprengen."""
    start = time.monotonic()
    res = requests.request(method, url, headers=headers, timeout=timeout, verify=verify, stream=True)
    try:
        body, truncated = read_limited(res, MAX_RESPONSE_BYTES)
    finally:
        res.close()
    return Fetched(response=res, body=body, truncated=truncated, duration_ms=elapsed_ms(start))

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
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/healthz")
async def healthz():
    return JSONResponse(content={"status": "ok"})

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")

@app.get("/")
async def get_home():
    return FileResponse(STATIC_DIR / "index.html")

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
    verify_tls: bool = True

    @field_validator("method", mode="before")
    @classmethod
    def _normalize_method(cls, v: object) -> str:
        method = str(v).upper()
        return method if method in ALLOWED_METHODS else "GET"

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
    status_code: int | None = None
    duration_ms: float | None = None
    truncated: bool = False
    headers: dict[str, str] = {}
    redirects: list[RedirectHop] = []

@app.post("/api/request", response_model=RequestOut)
async def post_request(data: RequestIn):
    timeout_value = clamp_timeout(data.timeout)

    async def work() -> RequestOut:
        fetched = await asyncio.to_thread(
            fetch, data.method, data.url,
            headers=parse_headers(data.headers), timeout=timeout_value, verify=data.verify_tls,
        )
        res = fetched.response
        redirects = [
            RedirectHop(status_code=hop.status_code, from_url=hop.url, location=hop.headers.get("Location", ""))
            for hop in res.history
        ]
        return RequestOut(
            response=decode_body(
                fetched.body, res.encoding,
                charset_declared="charset=" in res.headers.get("Content-Type", "").lower(),
                truncated=fetched.truncated,
            ),
            status_code=res.status_code,
            duration_ms=fetched.duration_ms,
            truncated=fetched.truncated,
            headers=dict(res.headers),
            redirects=redirects,
        )

    return await try_or_message(
        work,
        handlers=[(requests.exceptions.Timeout, lambda e: RequestOut(response=f"Timeout: {e}"))],
        default=lambda e: RequestOut(response=f"Fehler: {e}"),
    )

class RepeatIn(RequestIn):
    count: int = 5

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
    timeout_value = clamp_timeout(data.timeout)
    count = clamp_count(data.count)
    parsed_headers = parse_headers(data.headers)

    attempts: list[RepeatAttempt] = []
    for i in range(1, count + 1):
        start = time.monotonic()
        try:
            fetched = await asyncio.to_thread(
                fetch, data.method, data.url, headers=parsed_headers, timeout=timeout_value, verify=data.verify_tls
            )
            attempts.append(RepeatAttempt(
                attempt=i,
                status_code=fetched.response.status_code,
                duration_ms=fetched.duration_ms,
            ))
        except (requests.exceptions.RequestException, ValueError) as e:
            attempts.append(RepeatAttempt(
                attempt=i,
                duration_ms=elapsed_ms(start),
                error=str(e),
            ))

    # Latenz nur über Versuche mit HTTP-Antwort: ein sofortiges "connection refused" würde min/avg verfälschen
    durations = [a.duration_ms for a in attempts if a.status_code is not None and a.duration_ms is not None]
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
            (TimeoutError, lambda e: (f"Timeout: Hostname '{data.hostname}' nach {DNS_TIMEOUT}s nicht aufgelöst", [])),
            (socket.gaierror, lambda e: (f"Fehler: Hostname '{data.hostname}' nicht auflösbar: {e}", [])),
        ],
        default=lambda e: (f"Fehler (unerwartet): {e}", []),
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

class ChainHop(BaseModel):
    target: str
    status_code: int | None = None
    duration_ms: float | None = None
    error: str | None = None

class ChainRequest(BaseModel):
    message: str | None = None
    chain: list[str] = []
    timeout: float = CHAIN_TIMEOUT_DEFAULT

    @field_validator("timeout", mode="before")
    @classmethod
    def _coerce_timeout(cls, v: object) -> float:
        try:
            return float(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return CHAIN_TIMEOUT_DEFAULT

class ChainResponse(BaseModel):
    message: str | None = None
    final_status: int
    path: list[ChainHop]

class InvalidHopResponse(Exception):
    pass

def _parse_downstream(res: requests.Response) -> tuple[list[ChainHop], int]:
    try:
        body = res.json()
    except ValueError:
        raise InvalidHopResponse("Ungültige Antwort (kein JSON)") from None
    if not isinstance(body, dict):
        raise InvalidHopResponse("Ungültige Antwort (kein JSON-Objekt)")
    try:
        path = [ChainHop.model_validate(h) for h in body.get("path", [])]
    except (ValidationError, TypeError):
        raise InvalidHopResponse("Ungültige Antwort (unbekanntes path-Format)") from None
    final_status = body.get("final_status", res.status_code)
    return path, final_status if isinstance(final_status, int) else res.status_code

async def _call_next_hop(
    next_url: str, rest: list[str], data: ChainRequest, timeout_value: float
) -> tuple[list[ChainHop], int]:
    hop = ChainHop(target=next_url)
    start = time.monotonic()
    # Der nächste Hop wartet selbst bis zu timeout_value pro Hop auf den Rest der Kette. Ohne das
    # größere Lese-Budget liefe unser Timeout gleichzeitig ab und der Fehler landete beim falschen Hop.
    read_timeout = timeout_value * (len(rest) + 1)
    try:
        res = await asyncio.to_thread(
            requests.post,
            f"{next_url.rstrip('/')}/chain",
            json={"message": data.message, "chain": rest, "timeout": timeout_value},
            timeout=(timeout_value, read_timeout),
        )
        hop.duration_ms = elapsed_ms(start)
        hop.status_code = res.status_code
        try:
            downstream_path, final_status = _parse_downstream(res)
            path = [hop] + downstream_path
        except InvalidHopResponse as e:
            hop.error = str(e)
            path = [hop]
            final_status = 502
    except (requests.exceptions.RequestException, ValueError) as e:
        hop.duration_ms = elapsed_ms(start)
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
