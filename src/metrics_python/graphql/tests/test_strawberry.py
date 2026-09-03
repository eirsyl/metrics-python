from typing import Any

import pytest
import strawberry

from metrics_python.graphql import strawberry as extension
from metrics_python.graphql.strawberry import PrometheusExtensionSync


@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "world"


schema = strawberry.Schema(Query, extensions=[PrometheusExtensionSync])


class RecordingMetric:
    """Records the labels it is given and does nothing else."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def labels(self, **kwargs: Any) -> "RecordingMetric":
        self.calls.append(kwargs)
        return self

    def observe(self, value: float) -> None:
        return None

    @property
    def lifecycle_steps(self) -> set[Any]:
        return {call["lifecycle_step"] for call in self.calls}


@pytest.fixture
def lifecycle(monkeypatch: pytest.MonkeyPatch) -> RecordingMetric:
    """
    The metric is disabled by default and resolves at import, so the label
    values are checked where they are passed rather than where they land.
    """

    recorder = RecordingMetric()
    monkeypatch.setattr(extension, "LIFECYCLE_STEP_DURATION", recorder)
    return recorder


def test_lifecycle_step_is_labelled_with_the_enum_value(
    lifecycle: RecordingMetric,
) -> None:
    """
    LifecycleStep is an enum, and passing the member itself labels the metric
    "LifecycleStep.parse" instead of "parse". Nobody writing PromQL would guess
    that spelling.
    """

    result = schema.execute_sync("{ hello }")

    assert not result.errors
    assert lifecycle.lifecycle_steps == {"operation", "parse", "validation", "resolve"}


def test_the_enum_repr_is_never_used(lifecycle: RecordingMetric) -> None:
    schema.execute_sync("{ hello }")

    for step in lifecycle.lifecycle_steps:
        assert isinstance(step, str)
        assert not step.startswith("LifecycleStep")


def test_the_backend_is_always_labelled(lifecycle: RecordingMetric) -> None:
    schema.execute_sync("{ hello }")

    assert {call["backend"] for call in lifecycle.calls} == {"strawberry"}
