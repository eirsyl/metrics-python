from typing import Generator

import prometheus_client
import pytest


@pytest.fixture(autouse=True)
def reset_registry() -> Generator[None, None, None]:
    collectors = tuple(prometheus_client.REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            collector._metrics.clear()  # type: ignore
            collector._metric_init()  # type: ignore
        except AttributeError:
            pass  # built-in collectors don't inherit from MetricsWrapperBase
    yield
