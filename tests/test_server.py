import time
from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi.testclient import TestClient

from server import (
    MAX_CHAIN_HOPS,
    MAX_REQUEST_TIMEOUT,
    MIN_REQUEST_TIMEOUT,
    clamp_timeout,
    parse_headers,
)
from server import app as fastapi_app

client = TestClient(fastapi_app)


# --- clamp_timeout ---

@pytest.mark.parametrize(
    "value, expected",
    [
        (5.0, 5.0),
        (0.0, MIN_REQUEST_TIMEOUT),
        (-3.0, MIN_REQUEST_TIMEOUT),
        (100.0, MAX_REQUEST_TIMEOUT),
        (MIN_REQUEST_TIMEOUT, MIN_REQUEST_TIMEOUT),
        (MAX_REQUEST_TIMEOUT, MAX_REQUEST_TIMEOUT),
    ],
)
def test_clamp_timeout(value, expected):
    assert clamp_timeout(value) == expected


# --- parse_headers ---

def test_parse_headers_empty():
    assert parse_headers("") == {}

def test_parse_headers_single():
    assert parse_headers("X-Test: abc") == {"X-Test": "abc"}

def test_parse_headers_multiple_lines():
    raw = "X-A: 1\nX-B: 2"
    assert parse_headers(raw) == {"X-A": "1", "X-B": "2"}

def test_parse_headers_ignores_lines_without_colon():
    assert parse_headers("no-colon-here") == {}

def test_parse_headers_ignores_blank_lines():
    assert parse_headers("\n\nX-A: 1\n\n") == {"X-A": "1"}

def test_parse_headers_strips_whitespace():
    assert parse_headers("  X-A  :  1  ") == {"X-A": "1"}

def test_parse_headers_value_with_colon():
    assert parse_headers("X-Time: 12:30:00") == {"X-Time": "12:30:00"}


# --- /healthz ---

def test_healthz():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


# --- / ---

def test_get_home():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


# --- /api/request ---

def test_post_request_success():
    mock_response = MagicMock()
    mock_response.text = "hello world"
    mock_response.headers = {"Content-Type": "text/plain"}
    mock_response.history = []
    with patch("server.requests.request", return_value=mock_response) as mock_request:
        res = client.post("/api/request", json={"url": "http://example.local"})
    assert res.status_code == 200
    body = res.json()
    assert body["response"] == "hello world"
    assert body["headers"] == {"Content-Type": "text/plain"}
    assert body["redirects"] == []
    args, _kwargs = mock_request.call_args
    assert args[0] == "GET"
    assert args[1] == "http://example.local"

def test_post_request_follows_redirects():
    hop = MagicMock(status_code=301, url="http://example.local", headers={"Location": "http://example.local/new"})
    mock_response = MagicMock(text="ok", headers={}, history=[hop])
    with patch("server.requests.request", return_value=mock_response):
        res = client.post("/api/request", json={"url": "http://example.local"})
    body = res.json()
    assert body["redirects"] == [
        {"status_code": 301, "from_url": "http://example.local", "location": "http://example.local/new"}
    ]

def test_post_request_invalid_method_falls_back_to_get():
    mock_response = MagicMock(text="ok", headers={}, history=[])
    with patch("server.requests.request", return_value=mock_response) as mock_request:
        client.post("/api/request", json={"url": "http://example.local", "method": "TRACE"})
    args, _ = mock_request.call_args
    assert args[0] == "GET"

def test_post_request_method_is_uppercased():
    mock_response = MagicMock(text="ok", headers={}, history=[])
    with patch("server.requests.request", return_value=mock_response) as mock_request:
        client.post("/api/request", json={"url": "http://example.local", "method": "post"})
    args, _ = mock_request.call_args
    assert args[0] == "POST"

def test_post_request_invalid_timeout_defaults_to_5():
    captured = {}
    def fake_request(method, url, headers, timeout):
        captured["timeout"] = timeout
        return MagicMock(text="ok", headers={}, history=[])
    with patch("server.requests.request", side_effect=fake_request):
        client.post("/api/request", json={"url": "http://example.local", "timeout": "not-a-number"})
    assert captured["timeout"] == 5.0

def test_post_request_timeout_exception():
    with patch("server.requests.request", side_effect=requests.exceptions.Timeout("timed out")):
        res = client.post("/api/request", json={"url": "http://example.local"})
    assert res.status_code == 200
    assert "Timeout" in res.json()["response"]

def test_post_request_generic_exception():
    with patch("server.requests.request", side_effect=requests.exceptions.ConnectionError("refused")):
        res = client.post("/api/request", json={"url": "http://example.local"})
    assert res.status_code == 200
    assert "Fehler" in res.json()["response"]

def test_post_request_headers_are_parsed_and_forwarded():
    mock_response = MagicMock(text="ok", headers={}, history=[])
    with patch("server.requests.request", return_value=mock_response) as mock_request:
        client.post(
            "/api/request",
            json={"url": "http://example.local", "headers": "X-Test: abc\nX-Other: 1"},
        )
    _, kwargs = mock_request.call_args
    assert kwargs["headers"] == {"X-Test": "abc", "X-Other": "1"}


# --- /api/resolve ---

def test_resolve_hostname_success():
    with patch("server.socket.gethostbyname", return_value="127.0.0.1"):
        res = client.post("/api/resolve", json={"hostname": "localhost"})
    assert res.status_code == 200
    assert "127.0.0.1" in res.json()["result"]

def test_resolve_hostname_gaierror():
    import socket
    with patch("server.socket.gethostbyname", side_effect=socket.gaierror("not found")):
        res = client.post("/api/resolve", json={"hostname": "nonexistent.invalid"})
    assert res.status_code == 200
    assert "Fehler" in res.json()["result"]

def test_resolve_hostname_timeout():
    def slow_gethostbyname(hostname):
        time.sleep(0.2)
        return "127.0.0.1"

    with patch("server.DNS_TIMEOUT", 0.05), patch("server.socket.gethostbyname", side_effect=slow_gethostbyname):
        res = client.post("/api/resolve", json={"hostname": "slow.invalid"})
    assert res.status_code == 200
    assert "Timeout" in res.json()["result"]

def test_resolve_hostname_unexpected_exception():
    with patch("server.socket.gethostbyname", side_effect=RuntimeError("boom")):
        res = client.post("/api/resolve", json={"hostname": "example.local"})
    assert res.status_code == 200
    assert "unerwarteter Fehler" in res.json()["result"]


# --- /postbody ---

def test_post_body_echo():
    res = client.post("/postbody", json={"message": "Hallo Welt", "value": 42})
    assert res.status_code == 200
    assert res.json() == {"echo_message": "Hallo Welt", "echo_value": 42, "status": "ok"}

def test_post_body_validation_error():
    res = client.post("/postbody", json={"message": "no value"})
    assert res.status_code == 422


# --- /chain ---

def test_chain_empty_returns_immediately():
    res = client.post("/chain", json={"message": "hi", "chain": []})
    assert res.status_code == 200
    body = res.json()
    assert body["final_status"] == 200
    assert body["path"] == []

def test_chain_too_many_hops():
    chain = [f"http://host{i}" for i in range(MAX_CHAIN_HOPS + 1)]
    res = client.post("/chain", json={"message": "hi", "chain": chain})
    assert res.status_code == 200
    body = res.json()
    assert body["final_status"] == 400
    assert len(body["path"]) == 1
    assert "abgebrochen" in body["path"][0]["error"]

def test_chain_single_hop_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"final_status": 200, "path": []}
    with patch("server.requests.post", return_value=mock_response):
        res = client.post("/chain", json={"message": "hi", "chain": ["http://127.0.0.1:5091"]})
    body = res.json()
    assert body["final_status"] == 200
    assert len(body["path"]) == 1
    assert body["path"][0]["target"] == "http://127.0.0.1:5091"
    assert body["path"][0]["status_code"] == 200

def test_chain_hop_returns_non_json():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("no json")
    with patch("server.requests.post", return_value=mock_response):
        res = client.post("/chain", json={"message": "hi", "chain": ["http://127.0.0.1:5091"]})
    body = res.json()
    assert body["final_status"] == 502
    assert "kein JSON" in body["path"][0]["error"]

def test_chain_hop_unreachable():
    with patch("server.requests.post", side_effect=requests.exceptions.ConnectionError("refused")):
        res = client.post("/chain", json={"message": "hi", "chain": ["http://127.0.0.1:5999"]})
    body = res.json()
    assert body["final_status"] == 502
    assert len(body["path"]) == 1
    assert "refused" in body["path"][0]["error"]
