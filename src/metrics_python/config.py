import os
from itertools import pairwise
from logging import getLogger
from types import TracebackType
from typing import Any, Literal, Sequence, cast

from prometheus_client import Counter, Gauge, Histogram, Info, Summary

from .constants import NAMESPACE

logger = getLogger(__name__)

PREFIX = "METRICS_PYTHON_"

# Mirrors the modes prometheus-client accepts for a multiprocess gauge.
MultiprocessMode = Literal[
    "all",
    "liveall",
    "min",
    "livemin",
    "max",
    "livemax",
    "sum",
    "livesum",
    "mostrecent",
    "livemostrecent",
]

# The prometheus-client defaults. Every histogram uses these unless the
# environment overrides them.
DEFAULT_BUCKETS: tuple[float, ...] = tuple(Histogram.DEFAULT_BUCKETS)

INF = float("inf")

# Every metric the library can export, as <subsystem>_<name>. This is written
# out rather than collected as modules import, so that an application using one
# integration still gets a useful warning about a variable naming a metric from
# another. The factories check their key against it, so it cannot drift.
KNOWN_METRICS = frozenset(
    {
        "asgi_request_duration",
        "asgi_request_size",
        "asgi_response_size",
        "celery_task_apply_duration",
        "celery_task_execution_delay",
        "celery_task_execution_duration",
        "celery_task_last_execution",
        "celery_task_published",
        "django_api_decorator_view_duration",
        "django_cache_call_duration",
        "django_cache_call_gets_duration",
        "django_celery_duplicate_query_count",
        "django_celery_query_count",
        "django_celery_query_duration",
        "django_celery_query_request_count",
        "django_database_get_new_connection_duration",
        "django_database_init_connection_state_duration",
        "django_middleware_duration",
        "django_ninja_view_duration",
        "django_request_duration",
        "django_request_size",
        "django_response_size",
        "django_signal_duration",
        "django_view_duplicate_query_count",
        "django_view_query_count",
        "django_view_query_duration",
        "django_view_query_request_count",
        "generics_info_application",
        "generics_info_application_version",
        "generics_workers_workers_by_state",
        "graphql_lifecycle_step_duration",
        "graphql_operation_duration",
        "gunicorn_log_records",
        "gunicorn_request_duration",
        "gunicorn_workers",
    }
)

# Metrics that cost more than they are worth by default. Nothing on this list is
# used by any dashboard or recording rule we know of, and the duplicate query
# counters do work on every query to produce their value.
DEFAULT_DISABLED = frozenset(
    {
        "celery_task_last_execution",
        "django_celery_duplicate_query_count",
        "django_view_duplicate_query_count",
        "graphql_lifecycle_step_duration",
    }
)

# Printing duplicate queries is useless unless they are counted, so asking for
# the printout turns the counters on too.
_PRINT_DUPLICATE_QUERIES_ENABLES = frozenset(
    {
        "django_celery_duplicate_query_count",
        "django_view_duplicate_query_count",
    }
)

_TRUE = {"y", "yes", "t", "true", "on", "1"}
_FALSE = {"n", "no", "f", "false", "off", "0"}


def _parse_bool(value: str) -> bool | None:
    lowered = value.strip().lower()

    if lowered in _TRUE:
        return True

    if lowered in _FALSE:
        return False

    return None


def _env_bool(key: str, *, default: bool) -> bool:
    raw = os.environ.get(key)

    if raw is None:
        return default

    parsed = _parse_bool(raw)
    if parsed is not None:
        return parsed

    logger.warning(
        "Ignoring invalid %s=%r, expected a boolean such as true or false.", key, raw
    )

    return default


def print_duplicate_queries() -> bool:
    """
    Print duplicate queries and the stack that produced them to stdout. Meant
    for local debugging.
    """

    return _env_bool(f"{PREFIX}PRINT_DUPLICATE_QUERIES", default=False)


def metric_enabled(metric: str) -> bool:
    """
    Whether a metric should be exported.

    METRICS_PYTHON_<METRIC>_ENABLED decides, otherwise the metric is on unless
    it is in DEFAULT_DISABLED. Call this before doing expensive work to produce
    a value, disabling a metric should not just throw the value away.
    """

    key = f"{PREFIX}{metric.upper()}_ENABLED"
    raw = os.environ.get(key)

    if raw is not None:
        parsed = _parse_bool(raw)
        if parsed is not None:
            return parsed

        logger.warning(
            "Ignoring invalid %s=%r, expected a boolean such as true or false.",
            key,
            raw,
        )

    if metric in _PRINT_DUPLICATE_QUERIES_ENABLES and print_duplicate_queries():
        return True

    return metric not in DEFAULT_DISABLED


def _parse_buckets(raw: str) -> tuple[float, ...] | None:
    values: list[float] = []

    for part in raw.split(","):
        bound = part.strip()
        if not bound:
            continue

        try:
            values.append(float(bound))
        except ValueError:
            return None

    if not values:
        return None

    if any(current >= following for current, following in pairwise(values)):
        return None

    if all(value == INF for value in values):
        return None

    return tuple(values)


def buckets_for(metric: str) -> tuple[float, ...]:
    """
    Resolve the histogram buckets to use for a metric.

    METRICS_PYTHON_<METRIC>_BUCKETS wins, then METRICS_PYTHON_DEFAULT_BUCKETS,
    then the prometheus-client defaults. Invalid values are ignored with a
    warning rather than raising, a malformed environment variable should not
    stop an application from starting.

    Buckets are resolved when the metric is created, which is at import time.
    Every process exporting a metric has to resolve the same buckets, replicas
    that disagree produce a histogram Prometheus cannot aggregate.
    """

    for key in (f"{PREFIX}{metric.upper()}_BUCKETS", f"{PREFIX}DEFAULT_BUCKETS"):
        raw = os.environ.get(key)
        if raw is None:
            continue

        buckets = _parse_buckets(raw)
        if buckets is not None:
            return buckets

        logger.warning(
            "Ignoring invalid %s=%r, buckets must be a comma separated list of "
            "increasing numbers.",
            key,
            raw,
        )

    return DEFAULT_BUCKETS


class _NullMetric:
    """
    Stands in for a disabled metric. Accepts everything the real metrics accept
    and records nothing, so call sites do not need to know.
    """

    def labels(self, *args: Any, **kwargs: Any) -> "_NullMetric":
        return self

    def observe(self, *args: Any, **kwargs: Any) -> None:
        return None

    def inc(self, *args: Any, **kwargs: Any) -> None:
        return None

    def dec(self, *args: Any, **kwargs: Any) -> None:
        return None

    def set(self, *args: Any, **kwargs: Any) -> None:
        return None

    def set_to_current_time(self, *args: Any, **kwargs: Any) -> None:
        return None

    def info(self, *args: Any, **kwargs: Any) -> None:
        return None

    def time(self) -> "_NullMetric":
        return self

    def __enter__(self) -> "_NullMetric":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


def _key(name: str, subsystem: str) -> str:
    metric = f"{subsystem}_{name}"

    if metric not in KNOWN_METRICS:
        raise RuntimeError(
            f"{metric!r} is not in KNOWN_METRICS. Add it, otherwise it cannot be "
            f"configured and a typo in its environment variable goes unreported."
        )

    return metric


def histogram(
    name: str,
    documentation: str,
    labelnames: Sequence[str] = (),
    *,
    subsystem: str,
    unit: str = "",
) -> Histogram:
    metric = _key(name, subsystem)

    if not metric_enabled(metric):
        return cast(Histogram, _NullMetric())

    return Histogram(
        name,
        documentation,
        labelnames,
        unit=unit,
        buckets=buckets_for(metric),
        namespace=NAMESPACE,
        subsystem=subsystem,
    )


def counter(
    name: str,
    documentation: str,
    labelnames: Sequence[str] = (),
    *,
    subsystem: str,
) -> Counter:
    metric = _key(name, subsystem)

    if not metric_enabled(metric):
        return cast(Counter, _NullMetric())

    return Counter(
        name,
        documentation,
        labelnames,
        namespace=NAMESPACE,
        subsystem=subsystem,
    )


def gauge(
    name: str,
    documentation: str,
    labelnames: Sequence[str] = (),
    *,
    subsystem: str,
    multiprocess_mode: MultiprocessMode = "all",
) -> Gauge:
    metric = _key(name, subsystem)

    if not metric_enabled(metric):
        return cast(Gauge, _NullMetric())

    return Gauge(
        name,
        documentation,
        labelnames,
        multiprocess_mode=multiprocess_mode,
        namespace=NAMESPACE,
        subsystem=subsystem,
    )


def summary(
    name: str,
    documentation: str,
    labelnames: Sequence[str] = (),
    *,
    subsystem: str,
    unit: str = "",
) -> Summary:
    metric = _key(name, subsystem)

    if not metric_enabled(metric):
        return cast(Summary, _NullMetric())

    return Summary(
        name,
        documentation,
        labelnames,
        unit=unit,
        namespace=NAMESPACE,
        subsystem=subsystem,
    )


def info(
    name: str,
    documentation: str,
    *,
    subsystem: str,
) -> Info:
    metric = _key(name, subsystem)

    if not metric_enabled(metric):
        return cast(Info, _NullMetric())

    return Info(
        name,
        documentation,
        namespace=NAMESPACE,
        subsystem=subsystem,
    )


def _known_environment_variables() -> set[str]:
    known = {f"{PREFIX}DEFAULT_BUCKETS", f"{PREFIX}PRINT_DUPLICATE_QUERIES"}

    for metric in KNOWN_METRICS:
        known.add(f"{PREFIX}{metric.upper()}_ENABLED")
        known.add(f"{PREFIX}{metric.upper()}_BUCKETS")

    return known


def warn_about_unknown_environment_variables() -> None:
    """
    A misspelled variable silently does nothing, which is the worst outcome for
    a switch meant to keep costs down.
    """

    known = _known_environment_variables()

    for name in sorted(os.environ):
        if name.startswith(PREFIX) and name not in known:
            logger.warning(
                "Unknown environment variable %s, it does not name a "
                "metrics-python setting and has no effect.",
                name,
            )


warn_about_unknown_environment_variables()
