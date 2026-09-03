import strawberry
from prometheus_client import REGISTRY

from metrics_python.graphql.strawberry import PrometheusExtensionSync

COUNT = "metrics_python_graphql_lifecycle_step_duration_seconds_count"


@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "world"


schema = strawberry.Schema(Query, extensions=[PrometheusExtensionSync])


def test_lifecycle_step_is_labelled_with_the_enum_value() -> None:
    """
    LifecycleStep is an enum, and passing the member itself exports the Python
    repr, "LifecycleStep.parse", instead of "parse". Nobody writing PromQL would
    guess that spelling.
    """

    result = schema.execute_sync("{ hello }")

    assert not result.errors

    for step in ("operation", "parse", "validation", "resolve"):
        assert (
            REGISTRY.get_sample_value(
                COUNT, {"lifecycle_step": step, "backend": "strawberry"}
            )
            == 1.0
        ), f"no samples exported for lifecycle_step={step!r}"


def test_enum_repr_is_not_exported() -> None:
    schema.execute_sync("{ hello }")

    for step in ("LifecycleStep.OPERATION", "LifecycleStep.PARSE"):
        assert (
            REGISTRY.get_sample_value(
                COUNT, {"lifecycle_step": step, "backend": "strawberry"}
            )
            is None
        ), f"enum repr {step!r} is still being exported"
