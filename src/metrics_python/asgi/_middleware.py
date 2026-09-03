import time

from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.types import Message, Receive, Scope, Send

from metrics_python.generics.http import sanitize_http_method
from metrics_python.generics.workers import WORKERS_BY_STATE

from ._metrics import REQUEST_DURATION, REQUEST_SIZE, RESPONSE_SIZE


class ASGIMiddleware:
    def __init__(self, app: Starlette) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # Increase the in-progress metric
        # We cannot use the default export_worker_busy_state method is asgi
        # since one process may process multiple requests at the same time.
        inprogress = WORKERS_BY_STATE.labels(state="busy", worker_type="asgi")
        inprogress.inc()

        request = Request(scope)
        request_start_time = time.perf_counter()

        status_code = 500
        headers: list[tuple[bytes, bytes]] = []
        body_size = 0
        response_start_time = None

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                nonlocal status_code, headers, response_start_time
                headers = message["headers"]
                status_code = message["status"]
                response_start_time = time.perf_counter()
            elif message["type"] == "http.response.body" and "body" in message:
                # Count the bytes instead of collecting them. Holding on to the
                # body keeps a copy of every response in memory, and grows
                # without bound on a long lived stream.
                nonlocal body_size
                body_size += len(message["body"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            raise exc
        finally:
            duration_without_streaming = 0.0
            if response_start_time:
                duration_without_streaming = max(
                    response_start_time - request_start_time, 0.0
                )

            # Observe values.
            observe(
                request=request,
                status_code=status_code,
                response_headers=Headers(raw=headers),
                body_size=body_size,
                duration_without_streaming=duration_without_streaming,
            )

            # Decrease the in-progress metric.
            inprogress.dec()


def _content_length(headers: Headers, *, default: int) -> int:
    value = headers.get("Content-Length")

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def observe(
    *,
    request: Request,
    status_code: int,
    response_headers: Headers,
    body_size: int,
    duration_without_streaming: float,
) -> None:
    """Measure values."""

    status = str(status_code)
    method = sanitize_http_method(request.method)

    request_size = _content_length(request.headers, default=0)

    # Responses without a Content-Length, streaming responses in particular, are
    # measured by the number of body bytes that were sent.
    response_size = _content_length(response_headers, default=body_size)

    REQUEST_SIZE.labels(status=status, method=method).observe(request_size)
    RESPONSE_SIZE.labels(status=status, method=method).observe(response_size)

    REQUEST_DURATION.labels(status=status, method=method).observe(
        duration_without_streaming
    )
