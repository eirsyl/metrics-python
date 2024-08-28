from prometheus_client import Histogram, Summary

from ..constants import NAMESPACE

REQUEST_DURATION = Histogram(
    "request_duration",
    "Time spent on processing a request in the ASGI server",
    ["status", "method"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="asgi",
)

REQUEST_SIZE = Summary(
    "request_size",
    "HTTP request size in bytes.",
    ["status", "method"],
    unit="bytes",
    namespace=NAMESPACE,
    subsystem="asgi",
)

RESPONSE_SIZE = Summary(
    "response_size",
    "HTTP response size in bytes.",
    ["status", "method"],
    unit="bytes",
    namespace=NAMESPACE,
    subsystem="asgi",
)

COMBINED_SIZE = Summary(
    "combined_size",
    "HTTP request and response size combined in bytes.",
    ["status", "method"],
    unit="bytes",
    namespace=NAMESPACE,
    subsystem="asgi",
)
