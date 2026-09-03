from prometheus_client import Histogram

from ..buckets import buckets_for
from ..constants import NAMESPACE

VIEW_DURATION = Histogram(
    "view_duration",
    "Time spent on a django-ninja view.",
    ["method", "view", "status"],
    unit="seconds",
    buckets=buckets_for("django_ninja_view_duration"),
    namespace=NAMESPACE,
    subsystem="django_ninja",
)
