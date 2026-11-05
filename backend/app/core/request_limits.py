"""Limite de tamanho do corpo das requisições HTTP (responde 413)."""
from __future__ import annotations

import json

from fastapi import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send


def _detail(max_bytes: int) -> str:
    return f"Corpo da requisição acima do limite de {max_bytes} bytes."


class RequestBodyTooLarge(HTTPException):
    # Subclasse de HTTPException: o FastAPI a repassa sem convertê-la em 400 ao ler o corpo.
    def __init__(self, max_bytes: int) -> None:
        super().__init__(status_code=413, detail=_detail(max_bytes))


class BodySizeLimitMiddleware:
    """Recusa pelo Content-Length declarado e, sem ele (chunked), enquanto o corpo chega."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        for name, value in scope.get("headers", []):
            if name == b"content-length" and value.isdigit() and int(value) > self.max_bytes:
                await self._reject(send)
                return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestBodyTooLarge(self.max_bytes)
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except RequestBodyTooLarge:
            if not response_started:
                await self._reject(send)

    async def _reject(self, send: Send) -> None:
        body = json.dumps({"detail": _detail(self.max_bytes)}, ensure_ascii=False).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()),
                        (b"connection", b"close")],
        })
        await send({"type": "http.response.body", "body": body})
