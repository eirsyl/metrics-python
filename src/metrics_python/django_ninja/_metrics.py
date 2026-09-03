from ..config import histogram

VIEW_DURATION = histogram(
    "view_duration",
    "Time spent on a django-ninja view.",
    ["method", "view", "status"],
    unit="seconds",
    subsystem="django_ninja",
)
