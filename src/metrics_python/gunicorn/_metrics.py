from ..config import counter, gauge, histogram

REQUEST_DURATION = histogram(
    "request_duration",
    "Time spent on processing a request in Gunicorn",
    ["status", "method"],
    unit="seconds",
    subsystem="gunicorn",
)

LOG_RECORDS = counter(
    "log_records",
    "The number of log records emitted by Gunicorn.",
    ["level"],
    subsystem="gunicorn",
)


ACTIVE_WORKERS = gauge(
    "workers",
    "Active gunicorn workers",
    subsystem="gunicorn",
)
