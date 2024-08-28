import pytest
from prometheus_client import REGISTRY
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse, StreamingResponse
from starlette.routing import Route, WebSocketRoute
from starlette.testclient import TestClient

from metrics_python.asgi import ASGIMiddleware


def plain(request):
    return PlainTextResponse("Hello, world!")


async def generator():
    yield "a"
    yield "b"
    yield "c"


def stream(request):
    return StreamingResponse(generator(), media_type="text/plain")


async def websocket(websocket):
    await websocket.accept()
    await websocket.send_text("Hello, world!")
    await websocket.close()


routes = [
    Route("/plain/", plain),
    Route("/stream/", stream),
    WebSocketRoute("/websocket/", websocket),
]

app = Starlette(debug=True, routes=routes, middleware=[Middleware(ASGIMiddleware)])


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.asyncio
async def test_middleware_with_starlette_app_plain(client: TestClient) -> None:
    response = client.get("/plain/")
    assert response.status_code == 200

    assert (
        REGISTRY.get_sample_value(
            "metrics_python_asgi_request_duration_seconds_count",
            {"status": "200", "method": "GET"},
        )
        == 1.0
    )


@pytest.mark.asyncio
async def test_middleware_with_starlette_app_stream(client: TestClient) -> None:
    response = client.get("/stream/")
    assert response.status_code == 200

    assert (
        REGISTRY.get_sample_value(
            "metrics_python_asgi_request_duration_seconds_count",
            {"status": "200", "method": "GET"},
        )
        == 1.0
    )


@pytest.mark.asyncio
async def test_middleware_with_starlette_app_websocket(client: TestClient) -> None:
    with client.websocket_connect("/websocket/") as websocket:
        data = websocket.receive_text()
        assert data == "Hello, world!"

    assert (
        REGISTRY.get_sample_value(
            "metrics_python_asgi_request_duration_seconds_count",
            {"status": "200", "method": "GET"},
        )
        is None  # We currently does not support websockets.
    )
