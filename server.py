from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
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
        "response": response_text,
        "headers": {}
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