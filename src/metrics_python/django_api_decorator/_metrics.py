from prometheus_client import Histogram

from ..buckets import buckets_for
from ..constants import NAMESPACE

VIEW_DURATION = Histogram(
    "view_duration",
    "Time spent on a django-api-decorator view.",
    ["method", "view", "status"],
    unit="seconds",
    buckets=buckets_for("django_api_decorator_view_duration"),
    namespace=NAMESPACE,
    subsystem="django_api_decorator",
)
