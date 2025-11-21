from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests
import socket
import html
import logging
import signal
import sys

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def handle_sigterm(signum, frame):
    print("SIGTERM received. Shutting down gracefully...")

signal.signal(signal.SIGTERM, handle_sigterm)

logging.basicConfig(level=logging.INFO)

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
async def post_home(request: Request, url: str = Form(...)):
    response_text = ""
    response_headers = {}
    try:
        res = requests.get(url, timeout=5)
        response_text = res.text
        response_headers = dict(res.headers)
    except requests.exceptions.Timeout as e:
        response_text = f"Timeout: {e}"
    except Exception as e:
        response_text = f"Fehler: {e}"
    return templates.TemplateResponse("index.html", {
        "request": request,
        "response": response_text,
        "headers": response_headers
    })

@app.post("/resolve", response_class=HTMLResponse)
async def resolve_hostname(request: Request, hostname: str = Form(...)):
    response_text = ""
    try:
        ip_address = socket.gethostbyname(hostname)
        response_text = f"Hostname: {html.escape(hostname)} IP-Adresse: {html.escape(ip_address)}"
    except socket.gaierror as e:
        response_text = f"Fehler beim Auflösen des Hostnamens '{hostname}': {e}"
    except Exception as e:
        response_text = f"Ein unerwarteter Fehler ist aufgetreten: {e}"
    return templates.TemplateResponse("index.html", {
        "request": request,
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