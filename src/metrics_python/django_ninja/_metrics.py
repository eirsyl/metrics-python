from prometheus_client import Histogram

from ..constants import NAMESPACE

VIEW_DURATION = Histogram(
    "view_duration",
    "Time spent on a django-ninja view.",
    ["method", "view", "status"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="django_ninja",
)
