from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests
import socket
import html
import logging
import asyncio
import time

logging.basicConfig(level=logging.INFO)

DNS_TIMEOUT = 5.0
MAX_REQUEST_TIMEOUT = 30.0
ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "HEAD", "PATCH", "OPTIONS"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    logging.info("Shutdown event received. Shutting down gracefully...")

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/healthz")
async def healthz():
    return JSONResponse(content={"status": "ok"})

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse(request, "index.html")

def parse_headers(raw: str) -> dict[str, str]:
    headers = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        headers[key.strip()] = value.strip()
    return headers

@app.post("/", response_class=HTMLResponse)
async def post_home(
    request: Request,
    url: str = Form(...),
    method: str = Form("GET"),
    timeout: str = Form("5"),
    headers: str = Form(""),
):
    response_text = ""
    response_headers = {}
    method = method.upper() if method.upper() in ALLOWED_METHODS else "GET"
    try:
        timeout_value = min(float(timeout), MAX_REQUEST_TIMEOUT)
    except ValueError:
        timeout_value = 5.0
    try:
        res = await asyncio.to_thread(
            requests.request, method, url, headers=parse_headers(headers), timeout=timeout_value
        )
        response_text = res.text
        response_headers = dict(res.headers)
    except requests.exceptions.Timeout as e:
        response_text = f"Timeout: {e}"
    except Exception as e:
        response_text = f"Fehler: {e}"
    return templates.TemplateResponse(request, "index.html", {
        "response": response_text,
        "headers": response_headers
    })

@app.post("/resolve", response_class=HTMLResponse)
async def resolve_hostname(request: Request, hostname: str = Form(...)):
    response_text = ""
    try:
        ip_address = await asyncio.wait_for(
            asyncio.to_thread(socket.gethostbyname, hostname), timeout=DNS_TIMEOUT
        )
        response_text = f"Hostname: {html.escape(hostname)} IP-Adresse: {html.escape(ip_address)}"
    except asyncio.TimeoutError:
        response_text = f"Timeout beim Auflösen des Hostnamens '{hostname}' nach {DNS_TIMEOUT}s"
    except socket.gaierror as e:
        response_text = f"Fehler beim Auflösen des Hostnamens '{hostname}': {e}"
    except Exception as e:
        response_text = f"Ein unerwarteter Fehler ist aufgetreten: {e}"
    return templates.TemplateResponse(request, "index.html", {
        "dns_response": response_text,
        "active_tab": "hostname",
    })

class BodyData(BaseModel):
    message: str
    value: int

@app.post("/postbody")
async def post_body(data: BodyData):
    logging.info(f"Received body: {data}")
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
    hop = ChainHop(target=next_url)
    start = time.monotonic()
    try:
        res = await asyncio.to_thread(
            requests.post,
            f"{next_url.rstrip('/')}/chain",
            json={"message": data.message, "chain": rest, "timeout": data.timeout},
            timeout=data.timeout,
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
    except requests.exceptions.RequestException as e:
        hop.duration_ms = round((time.monotonic() - start) * 1000, 1)
        hop.error = str(e)
        path = [hop]
        final_status = 502

    return ChainResponse(message=data.message, final_status=final_status, path=path)

@app.post("/chain", response_model=ChainResponse)
async def chain(data: ChainRequest):
    return await run_chain(data)

@app.post("/chain-form", response_class=HTMLResponse)
async def chain_form(
    request: Request,
    message: str = Form(""),
    chain_urls: str = Form(""),
    timeout: str = Form("5"),
):
    urls = [line.strip() for line in chain_urls.splitlines() if line.strip()]
    try:
        timeout_value = min(float(timeout), MAX_REQUEST_TIMEOUT)
    except ValueError:
        timeout_value = CHAIN_TIMEOUT_DEFAULT

    result = await run_chain(ChainRequest(message=message or None, chain=urls, timeout=timeout_value))
    return templates.TemplateResponse(request, "index.html", {
        "chain_result": result,
        "active_tab": "chain",
    })