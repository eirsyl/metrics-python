import os
from itertools import pairwise
from logging import getLogger

from prometheus_client import Histogram

logger = getLogger(__name__)

# The prometheus-client defaults. Every histogram in metrics-python uses these
# unless the environment overrides them.
DEFAULT_BUCKETS: tuple[float, ...] = tuple(Histogram.DEFAULT_BUCKETS)

ENV_PREFIX = "METRICS_PYTHON_BUCKETS_"

INF = float("inf")


def _parse(raw: str) -> tuple[float, ...] | None:
    """
    Parse a comma separated list of bucket upper bounds. Returns None if the
    value is not something prometheus-client would accept.
    """

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

    The metric name is the exported name without the metrics_python prefix and
    without the unit suffix, so metrics_python_django_middleware_duration_seconds
    is configured with METRICS_PYTHON_BUCKETS_DJANGO_MIDDLEWARE_DURATION.

    METRICS_PYTHON_BUCKETS_DEFAULT applies to every histogram without a metric
    specific override. Invalid values are ignored with a warning instead of
    raising, a malformed environment variable should not prevent an application
    from starting.

    Buckets are resolved when the metric is created, which means at import time.
    Every process exporting a metric has to resolve the same buckets, replicas
    that disagree produce a histogram Prometheus cannot aggregate.
    """

    for key in (f"{ENV_PREFIX}{metric.upper()}", f"{ENV_PREFIX}DEFAULT"):
        raw = os.environ.get(key)
        if raw is None:
            continue

        buckets = _parse(raw)
        if buckets is not None:
            return buckets

        logger.warning(
            "Ignoring invalid %s=%r, buckets must be a comma separated list of "
            "increasing numbers.",
            key,
            raw,
        )

    return DEFAULT_BUCKETS
