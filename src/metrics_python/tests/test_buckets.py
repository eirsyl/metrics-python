import importlib

import pytest
from prometheus_client import Histogram

from metrics_python.buckets import DEFAULT_BUCKETS, buckets_for

# Every histogram in the library, as (module, attribute, metric key). The keys
# are the environment variable suffixes consumers configure, so a rename here is
# a breaking change for them.
HISTOGRAMS = [
    ("metrics_python.asgi._metrics", "REQUEST_DURATION", "asgi_request_duration"),
    (
        "metrics_python.celery._metrics",
        "TASK_APPLY_DURATION",
        "celery_task_apply_duration",
    ),
    (
        "metrics_python.celery._metrics",
        "TASK_EXECUTION_DELAY",
        "celery_task_execution_delay",
    ),
    (
        "metrics_python.celery._metrics",
        "TASK_EXECUTION_DURATION",
        "celery_task_execution_duration",
    ),
    ("metrics_python.django._metrics", "REQUEST_DURATION", "django_request_duration"),
    (
        "metrics_python.django._metrics",
        "CACHE_CALL_DURATION",
        "django_cache_call_duration",
    ),
    (
        "metrics_python.django._metrics",
        "CACHE_CALL_GETS_DURATION",
        "django_cache_call_gets_duration",
    ),
    (
        "metrics_python.django._metrics",
        "VIEW_QUERY_DURATION",
        "django_view_query_duration",
    ),
    (
        "metrics_python.django._metrics",
        "CELERY_QUERY_DURATION",
        "django_celery_query_duration",
    ),
    (
        "metrics_python.django._metrics",
        "DATABASE_GET_NEW_CONNECTION_HISTOGRAM",
        "django_database_get_new_connection_duration",
    ),
    (
        "metrics_python.django._metrics",
        "DATABASE_INIT_CONNECTION_STATE_HISTOGRAM",
        "django_database_init_connection_state_duration",
    ),
    ("metrics_python.django._metrics", "SIGNAL_DURATION", "django_signal_duration"),
    (
        "metrics_python.django._metrics",
        "MIDDLEWARE_DURATION",
        "django_middleware_duration",
    ),
    (
        "metrics_python.django_api_decorator._metrics",
        "VIEW_DURATION",
        "django_api_decorator_view_duration",
    ),
    (
        "metrics_python.django_ninja._metrics",
        "VIEW_DURATION",
        "django_ninja_view_duration",
    ),
    (
        "metrics_python.graphql._metrics",
        "OPERATION_DURATION",
        "graphql_operation_duration",
    ),
    (
        "metrics_python.graphql._metrics",
        "LIFECYCLE_STEP_DURATION",
        "graphql_lifecycle_step_duration",
    ),
    (
        "metrics_python.gunicorn._metrics",
        "REQUEST_DURATION",
        "gunicorn_request_duration",
    ),
]


def test_default_is_the_prometheus_client_default() -> None:
    """
    Making buckets configurable must not change what anybody exports today.
    Dashboards and SLO recording rules select individual le values, so a change
    here silently breaks them.
    """

    assert DEFAULT_BUCKETS == tuple(Histogram.DEFAULT_BUCKETS)


@pytest.mark.parametrize(("module", "attribute", "metric"), HISTOGRAMS)
def test_histograms_use_the_default_buckets(
    module: str, attribute: str, metric: str
) -> None:
    histogram = getattr(importlib.import_module(module), attribute)

    assert histogram._upper_bounds == list(DEFAULT_BUCKETS)


def test_every_histogram_is_configurable() -> None:
    """
    A histogram that never calls buckets_for cannot be tuned, which is the whole
    point of the environment variables.
    """

    configured = {metric for _, _, metric in HISTOGRAMS}

    assert len(configured) == len(HISTOGRAMS), "metric keys must be unique"
    assert len(HISTOGRAMS) == 18


def test_metric_specific_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "METRICS_PYTHON_BUCKETS_DJANGO_SIGNAL_DURATION", "0.001, 0.01, 0.1"
    )

    assert buckets_for("django_signal_duration") == (0.001, 0.01, 0.1)


def test_default_override_applies_to_every_metric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METRICS_PYTHON_BUCKETS_DEFAULT", "0.5,1,5")

    assert buckets_for("asgi_request_duration") == (0.5, 1.0, 5.0)
    assert buckets_for("celery_task_execution_delay") == (0.5, 1.0, 5.0)


def test_metric_specific_override_wins_over_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METRICS_PYTHON_BUCKETS_DEFAULT", "0.5,1,5")
    monkeypatch.setenv("METRICS_PYTHON_BUCKETS_ASGI_REQUEST_DURATION", "0.25")

    assert buckets_for("asgi_request_duration") == (0.25,)
    assert buckets_for("gunicorn_request_duration") == (0.5, 1.0, 5.0)


def test_infinity_is_accepted_as_the_final_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METRICS_PYTHON_BUCKETS_ASGI_REQUEST_DURATION", "0.1,1,inf")

    assert buckets_for("asgi_request_duration") == (0.1, 1.0, float("inf"))


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "not-a-number",
        "0.1,abc,1",
        "1,0.5",  # not increasing
        "0.1,0.1",  # duplicate would export two identical le series
        "inf",  # prometheus-client needs at least one finite bucket
    ],
)
def test_invalid_values_fall_back_to_the_default(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("METRICS_PYTHON_BUCKETS_ASGI_REQUEST_DURATION", value)

    assert buckets_for("asgi_request_duration") == DEFAULT_BUCKETS


def test_invalid_metric_override_falls_back_to_the_default_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METRICS_PYTHON_BUCKETS_DEFAULT", "0.5,1")
    monkeypatch.setenv("METRICS_PYTHON_BUCKETS_ASGI_REQUEST_DURATION", "nonsense")

    assert buckets_for("asgi_request_duration") == (0.5, 1.0)


def test_resolved_buckets_are_accepted_by_prometheus_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Anything buckets_for returns has to survive Histogram construction, an
    invalid value must never reach prometheus-client and raise at import.
    """

    monkeypatch.setenv("METRICS_PYTHON_BUCKETS_DEFAULT", "0.001,0.5,2.5")

    histogram = Histogram(
        "buckets_probe",
        "Probe.",
        buckets=buckets_for("anything"),
        namespace="metrics_python_test",
    )

    assert histogram._upper_bounds == [0.001, 0.5, 2.5, float("inf")]
