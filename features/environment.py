import os
import socket
import subprocess
import sys
import time

CHAIN_PORTS = [5091, 5092]
_procs = []


def _wait_for_port(port, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"Server auf Port {port} nicht erreichbar")


def before_all(context):
    env = os.environ.copy()
    for port in CHAIN_PORTS:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(port)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _procs.append(proc)
    for port in CHAIN_PORTS:
        _wait_for_port(port)
    context.chain_ports = CHAIN_PORTS


def after_all(context):
    for proc in _procs:
        proc.terminate()
    for proc in _procs:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
