"""Local access and resource boundaries exercised independently of routes."""
import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.security import LocalRequestBoundary


def isolated_app():
    app = FastAPI()
    app.add_middleware(LocalRequestBoundary, allowed_origins=["http://localhost:5173"])

    @app.post("/write")
    def write(payload: dict):
        return payload

    return app


def test_browser_and_host_boundaries():
    with TestClient(isolated_app(), base_url="http://localhost") as client:
        assert client.post("/write", json={}, headers={"origin": "https://attacker.invalid"}).status_code == 403
        assert client.post("/write", json={}, headers={"host": "attacker.invalid"}).status_code == 400
        assert client.post("/write", json={}, headers={"origin": "null"}).status_code == 403
        assert client.post("/write", json={}, headers={"origin": "http://localhost:5173"}).status_code == 200
        assert client.post("/write", json={}).status_code == 200
        assert client.post("/write", content='{}', headers={"content-type": "text/plain"}).status_code == 415
        assert client.post("/write", content='{}').status_code == 415
        assert client.post("/write", content='x' * 1_048_577, headers={"content-type": "application/json"}).status_code == 413


def test_streamed_body_limit_without_content_length():
    responses = []
    messages = iter([
        {"type": "http.request", "body": b"a" * 700_000, "more_body": True},
        {"type": "http.request", "body": b"b" * 700_000, "more_body": False},
    ])
    async def receive():
        return next(messages)
    async def send(message):
        responses.append(message)
    asyncio.run(isolated_app()({"type": "http", "method": "POST", "path": "/write", "headers": [(b"host", b"localhost"), (b"content-type", b"application/json")]}, receive, send))
    assert responses[0]["status"] == 413


@pytest.mark.parametrize("origin", ["*", "https://attacker.invalid", "http://localhost:5173/path", "null"])
def test_config_rejects_nonlocal_origins(origin):
    with pytest.raises(ValueError):
        Settings(_env_file=None, cors_origins=origin)
