import time

from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Message, Receive, Scope, Send

from metrics_python.generics.http import sanitize_http_method
from metrics_python.generics.workers import WORKERS_BY_STATE

from ._metrics import COMBINED_SIZE, REQUEST_DURATION, REQUEST_SIZE, RESPONSE_SIZE


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
        headers = []
        body = b""
        response_start_time = None

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                nonlocal status_code, headers, response_start_time
                headers = message["headers"]
                status_code = message["status"]
                response_start_time = time.perf_counter()
            elif message["type"] == "http.response.body" and "body" in message:
                nonlocal body
                body += message["body"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            raise exc
        finally:
            response = Response(
                content=body, headers=Headers(raw=headers), status_code=status_code
            )

            duration_without_streaming = 0.0
            if response_start_time:
                duration_without_streaming = max(
                    response_start_time - request_start_time, 0.0
                )

            # Observe values.
            observe(
                request=request,
                response=response,
                duration_without_streaming=duration_without_streaming,
            )

            # Decrease the in-progress metric.
            inprogress.dec()


def observe(
    *,
    request: Request,
    response: Response,
    duration_without_streaming: float,
) -> None:
    """Measure values."""

    status = str(response.status_code)
    method = sanitize_http_method(request.method)

    request_size = int(request.headers.get("Content-Length", 0))
    response_size = (
        int(response.headers.get("Content-Length", 0))
        if hasattr(response, "headers")
        else 0
    )

    REQUEST_SIZE.labels(status=status, method=method).observe(request_size)
    RESPONSE_SIZE.labels(status=status, method=method).observe(response_size)
    COMBINED_SIZE.labels(status=status, method=method).observe(
        request_size + response_size
    )

    REQUEST_DURATION.labels(status=status, method=method).observe(
        duration_without_streaming
    )
