import pytest
from fastapi import FastAPI, WebSocket
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from metrics_python.asgi import ASGIMiddleware

app = FastAPI()
app.add_middleware(ASGIMiddleware)


@app.get("/plain/")
async def plain():
    return "Hello, world!"


async def generator():
    yield "a"
    yield "b"
    yield "c"


@app.get("/stream/")
def stream():
    return StreamingResponse(generator(), media_type="text/plain")


@app.websocket("/websocket/")
async def websocket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello, world!")
    await websocket.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.asyncio
async def test_middleware_with_fastapi_app_plain(client: TestClient) -> None:
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
async def test_middleware_with_fastapi_app_stream(client: TestClient) -> None:
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
async def test_middleware_with_fastapi_app_websocket(client: TestClient) -> None:
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
