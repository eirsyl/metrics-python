from typing import Any

from django.test import Client
from prometheus_client import REGISTRY


def test_ninja_middleware(client: Client, settings: Any) -> None:
    settings.MIDDLEWARE = ["metrics_python.django_ninja.DjangoNinjaMetricsMiddleware"]

    response = client.get("/ninja/get")
    assert response.status_code == 200

    assert (
        REGISTRY.get_sample_value(
            "metrics_python_django_ninja_view_duration_seconds_count",
            {"status": "200", "view": "api-1.0.0:get", "method": "GET"},
        )
        == 1.0
    )

    response = client.get("/ninja/get-operation-id")
    assert response.status_code == 200

    assert (
        REGISTRY.get_sample_value(
            "metrics_python_django_ninja_view_duration_seconds_count",
            {"status": "200", "view": "get-operation-id", "method": "GET"},
        )
        == 1.0
    )

    # Make sure normal views continue to work as usual.

    response = client.get("/get")
    assert response.status_code == 200

    assert (
        REGISTRY.get_sample_value(
            "metrics_python_django_ninja_view_duration_seconds_count",
            {"status": "200", "view": "api-1.0.0:get", "method": "GET"},
        )
        == 1.0
    )
