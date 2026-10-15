"""Local deployment guardrails, not authentication or tenant isolation."""
from urllib.parse import urlsplit

from starlette.responses import JSONResponse


class LocalRequestBoundary:
    def __init__(self, app, allowed_origins: list[str], max_body_bytes: int = 1_048_576):
        self.app = app
        self.allowed_origins = set(allowed_origins)
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {key.lower(): value for key, value in scope.get("headers", [])}

        async def reject(code, detail):
            await JSONResponse({"detail": detail}, status_code=code)(scope, receive, send)

        host = headers.get(b"host", b"").decode("latin1")
        try:
            hostname = urlsplit(f"http://{host}").hostname
        except ValueError:
            hostname = None
        test_client = (scope.get("client") or (None,))[0] == "testclient"
        if hostname not in {"localhost", "127.0.0.1", "::1"} and not (test_client and hostname == "testserver"):
            return await reject(400, "Only loopback hosts are supported")
        origin = headers.get(b"origin")
        if origin is not None and origin.decode("latin1") not in self.allowed_origins:
            return await reject(403, "Browser origin is not allowed")
        if scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        content_type = headers.get(b"content-type", b"").split(b";", 1)[0].strip().lower()
        # Empty-body evaluation requests remain valid for command-line clients.
        if content_type and content_type != b"application/json":
            return await reject(415, "Use application/json for writes")
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                return await reject(400, "Invalid content length")
            if length < 0:
                return await reject(400, "Invalid content length")
            if length > self.max_body_bytes:
                return await reject(413, "Request body exceeds 1 MiB")
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            size += len(body)
            if size > self.max_body_bytes:
                return await reject(413, "Request body exceeds 1 MiB")
            chunks.append(body)
            if not message.get("more_body", False):
                break
        if size and content_type != b"application/json":
            return await reject(415, "Use application/json for writes")
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
