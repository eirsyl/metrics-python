import importlib

import pytest
from prometheus_client import Histogram

from metrics_python.config import (
    DEFAULT_BUCKETS,
    DEFAULT_DISABLED,
    KNOWN_METRICS,
    _NullMetric,
    buckets_for,
    metric_enabled,
    warn_about_unknown_environment_variables,
)

# Modules that declare metrics, imported to prove every declaration resolves.
METRIC_MODULES = [
    "metrics_python.asgi._metrics",
    "metrics_python.celery._metrics",
    "metrics_python.django._metrics",
    "metrics_python.django_api_decorator._metrics",
    "metrics_python.django_ninja._metrics",
    "metrics_python.generics.info",
    "metrics_python.generics.workers",
    "metrics_python.graphql._metrics",
    "metrics_python.gunicorn._metrics",
]

# Histograms, as (module, attribute, metric key).
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


#
# Registry
#


def test_known_metrics_matches_what_is_declared() -> None:
    """
    KNOWN_METRICS is written out by hand so a typo can be reported without
    importing every integration. The factories reject a key that is missing
    from it, so importing everything proves the two agree.
    """

    for module in METRIC_MODULES:
        importlib.import_module(module)

    assert len(KNOWN_METRICS) == 35


def test_default_disabled_are_known_metrics() -> None:
    assert DEFAULT_DISABLED <= KNOWN_METRICS


#
# Enabling and disabling
#


def test_metrics_are_enabled_by_default() -> None:
    for metric in KNOWN_METRICS - DEFAULT_DISABLED:
        assert metric_enabled(metric), metric


def test_costly_and_unused_metrics_are_disabled_by_default() -> None:
    """
    These four are off because nothing reads them and they are not free. The
    two duplicate query counters walk the stack on every query, and the other
    two have no dashboard or recording rule anywhere.
    """

    assert DEFAULT_DISABLED == {
        "celery_task_last_execution",
        "django_celery_duplicate_query_count",
        "django_view_duplicate_query_count",
        "graphql_lifecycle_step_duration",
    }

    for metric in DEFAULT_DISABLED:
        assert not metric_enabled(metric), metric


def test_a_disabled_metric_can_be_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("METRICS_PYTHON_CELERY_TASK_LAST_EXECUTION_ENABLED", "true")

    assert metric_enabled("celery_task_last_execution")


def test_an_enabled_metric_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("METRICS_PYTHON_DJANGO_SIGNAL_DURATION_ENABLED", "false")

    assert not metric_enabled("django_signal_duration")


@pytest.mark.parametrize("value", ["yes", "on", "1", "TRUE", " true "])
def test_truthy_values(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("METRICS_PYTHON_CELERY_TASK_LAST_EXECUTION_ENABLED", value)

    assert metric_enabled("celery_task_last_execution")


def test_invalid_flag_falls_back_to_the_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METRICS_PYTHON_DJANGO_SIGNAL_DURATION_ENABLED", "maybe")

    assert metric_enabled("django_signal_duration")


def test_printing_duplicate_queries_enables_counting_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Printing is useless unless the queries are counted, so one flag is enough
    to get the local debugging behaviour.
    """

    assert not metric_enabled("django_view_duplicate_query_count")

    monkeypatch.setenv("METRICS_PYTHON_PRINT_DUPLICATE_QUERIES", "true")

    assert metric_enabled("django_view_duplicate_query_count")
    assert metric_enabled("django_celery_duplicate_query_count")


def test_an_explicit_flag_still_wins_over_printing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METRICS_PYTHON_PRINT_DUPLICATE_QUERIES", "true")
    monkeypatch.setenv(
        "METRICS_PYTHON_DJANGO_VIEW_DUPLICATE_QUERY_COUNT_ENABLED", "false"
    )

    assert not metric_enabled("django_view_duplicate_query_count")


#
# Disabled metrics
#


def test_a_disabled_metric_accepts_everything_and_records_nothing() -> None:
    metric = _NullMetric()

    metric.labels(a="b").observe(1.0)
    metric.labels(a="b").inc()
    metric.labels(a="b").dec()
    metric.labels(a="b").set(2.0)
    metric.labels(a="b").set_to_current_time()
    metric.info({"a": "b"})

    with metric.labels(a="b").time():
        pass


def test_a_disabled_metric_exports_no_series(monkeypatch: pytest.MonkeyPatch) -> None:
    from metrics_python.config import histogram

    monkeypatch.setenv("METRICS_PYTHON_DJANGO_SIGNAL_DURATION_ENABLED", "false")

    metric = histogram(
        "signal_duration", "...", ["signal"], unit="seconds", subsystem="django"
    )

    assert isinstance(metric, _NullMetric)


def test_declaring_an_unknown_metric_is_refused() -> None:
    from metrics_python.config import counter

    with pytest.raises(RuntimeError, match="KNOWN_METRICS"):
        counter("not_a_real_metric", "...", subsystem="django")


#
# Buckets
#


def test_default_is_the_prometheus_client_default() -> None:
    """
    Dashboards and SLO recording rules select individual le values, so the
    defaults must not move without someone deciding to move them.
    """

    assert DEFAULT_BUCKETS == tuple(Histogram.DEFAULT_BUCKETS)


@pytest.mark.parametrize(("module", "attribute", "metric"), HISTOGRAMS)
def test_histograms_use_the_default_buckets(
    module: str, attribute: str, metric: str
) -> None:
    histogram = getattr(importlib.import_module(module), attribute)

    if metric in DEFAULT_DISABLED:
        assert isinstance(histogram, _NullMetric)
        return

    assert histogram._upper_bounds == list(DEFAULT_BUCKETS)


def test_every_histogram_is_accounted_for() -> None:
    assert len({metric for _, _, metric in HISTOGRAMS}) == 18


def test_metric_specific_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "METRICS_PYTHON_DJANGO_SIGNAL_DURATION_BUCKETS", "0.001, 0.01, 0.1"
    )

    assert buckets_for("django_signal_duration") == (0.001, 0.01, 0.1)


def test_default_override_applies_to_every_metric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METRICS_PYTHON_DEFAULT_BUCKETS", "0.5,1,5")

    assert buckets_for("asgi_request_duration") == (0.5, 1.0, 5.0)
    assert buckets_for("celery_task_execution_delay") == (0.5, 1.0, 5.0)


def test_metric_specific_override_wins_over_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METRICS_PYTHON_DEFAULT_BUCKETS", "0.5,1,5")
    monkeypatch.setenv("METRICS_PYTHON_ASGI_REQUEST_DURATION_BUCKETS", "0.25")

    assert buckets_for("asgi_request_duration") == (0.25,)
    assert buckets_for("gunicorn_request_duration") == (0.5, 1.0, 5.0)


def test_infinity_is_accepted_as_the_final_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METRICS_PYTHON_ASGI_REQUEST_DURATION_BUCKETS", "0.1,1,inf")

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
def test_invalid_buckets_fall_back_to_the_default(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("METRICS_PYTHON_ASGI_REQUEST_DURATION_BUCKETS", value)

    assert buckets_for("asgi_request_duration") == DEFAULT_BUCKETS


def test_invalid_metric_buckets_fall_back_to_the_default_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METRICS_PYTHON_DEFAULT_BUCKETS", "0.5,1")
    monkeypatch.setenv("METRICS_PYTHON_ASGI_REQUEST_DURATION_BUCKETS", "nonsense")

    assert buckets_for("asgi_request_duration") == (0.5, 1.0)


def test_resolved_buckets_are_accepted_by_prometheus_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METRICS_PYTHON_DEFAULT_BUCKETS", "0.001,0.5,2.5")

    metric = Histogram(
        "buckets_probe",
        "Probe.",
        buckets=buckets_for("asgi_request_duration"),
        namespace="metrics_python_test",
    )

    assert metric._upper_bounds == [0.001, 0.5, 2.5, float("inf")]


#
# Typos
#


def test_unknown_variables_are_reported(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """
    A misspelled flag silently does nothing, which is the worst outcome for a
    switch meant to keep costs down.
    """

    monkeypatch.setenv("METRICS_PYTHON_DJANGO_SIGNAL_DURATON_ENABLED", "false")

    with caplog.at_level("WARNING"):
        warn_about_unknown_environment_variables()

    assert "METRICS_PYTHON_DJANGO_SIGNAL_DURATON_ENABLED" in caplog.text


def test_recognised_variables_are_not_reported(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("METRICS_PYTHON_DJANGO_SIGNAL_DURATION_ENABLED", "false")
    monkeypatch.setenv("METRICS_PYTHON_DJANGO_SIGNAL_DURATION_BUCKETS", "0.1")
    monkeypatch.setenv("METRICS_PYTHON_DEFAULT_BUCKETS", "0.1")
    monkeypatch.setenv("METRICS_PYTHON_PRINT_DUPLICATE_QUERIES", "true")

    with caplog.at_level("WARNING"):
        warn_about_unknown_environment_variables()

    assert "METRICS_PYTHON_" not in caplog.text
