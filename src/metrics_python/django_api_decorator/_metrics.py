from ..config import histogram

VIEW_DURATION = histogram(
    "view_duration",
    "Time spent on a django-api-decorator view.",
    ["method", "view", "status"],
    unit="seconds",
    subsystem="django_api_decorator",
)
