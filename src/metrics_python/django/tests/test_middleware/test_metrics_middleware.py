from typing import Any

from django.test import Client
from prometheus_client import REGISTRY


def test_metrics_middleware(client: Client, settings: Any) -> None:
    settings.MIDDLEWARE = [
        "metrics_python.django.middleware.MetricsMiddleware",
        "django.middleware.common.CommonMiddleware",
    ]

    response = client.get("/get")
    assert response.status_code == 200

    assert (
        REGISTRY.get_sample_value(
            "metrics_python_django_request_duration_seconds_count",
            {
                "status": "200",
                "view": "metrics_python.django.tests.app.view.get",
                "method": "GET",
            },
        )
        == 1.0
    )
