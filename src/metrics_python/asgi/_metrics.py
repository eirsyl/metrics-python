from ..config import histogram, summary

REQUEST_DURATION = histogram(
    "request_duration",
    "Time spent on processing a request in the ASGI server",
    ["status", "method"],
    unit="seconds",
    subsystem="asgi",
)

REQUEST_SIZE = summary(
    "request_size",
    "HTTP request size in bytes.",
    ["status", "method"],
    unit="bytes",
    subsystem="asgi",
)

RESPONSE_SIZE = summary(
    "response_size",
    "HTTP response size in bytes.",
    ["status", "method"],
    unit="bytes",
    subsystem="asgi",
)
