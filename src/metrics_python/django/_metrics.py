from ..config import counter, histogram, summary

#
# Views
#

REQUEST_DURATION = histogram(
    "request_duration",
    "Time spent on processing a request in the ASGI server",
    ["status", "view", "method"],
    unit="seconds",
    subsystem="django",
)

REQUEST_SIZE = summary(
    "request_size",
    "HTTP request size in bytes.",
    ["status", "view", "method"],
    unit="bytes",
    subsystem="django",
)

RESPONSE_SIZE = summary(
    "response_size",
    "HTTP response size in bytes.",
    ["status", "view", "method"],
    unit="bytes",
    subsystem="django",
)


#
# Cache
#

CACHE_CALL_DURATION = histogram(
    "cache_call_duration",
    "Cache call duration by method and alias.",
    ["alias", "method"],
    unit="seconds",
    subsystem="django",
)

CACHE_CALL_GETS_DURATION = histogram(
    "cache_call_gets_duration",
    "Cache call duration for get requests by cache hit, alias and method.",
    ["alias", "method", "hit"],
    unit="seconds",
    subsystem="django",
)

#
# Django view query counts
#

# This counter is used to calculate the average number of
# sql queries executed by a view.
VIEW_QUERY_REQUESTS_COUNT = counter(
    "view_query_request_count",
    "Number of requests sent to a view.",
    ["method", "view", "status"],
    subsystem="django",
)

VIEW_QUERY_DURATION = histogram(
    "view_query_duration",
    "Database query duration by views.",
    ["db", "method", "view", "status"],
    unit="seconds",
    subsystem="django",
)

VIEW_QUERY_COUNT = counter(
    "view_query_count",
    "Number of database queries executed by views.",
    ["db", "method", "view", "status"],
    subsystem="django",
)

VIEW_DUPLICATE_QUERY_COUNT = counter(
    "view_duplicate_query_count",
    "Number of duplicate database queries executed by views.",
    ["db", "method", "view", "status"],
    subsystem="django",
)


#
# Django Celery task query counts
#

# This counter is used to calculate the average number of
# sql queries executed by a task.
CELERY_QUERY_REQUESTS_COUNT = counter(
    "celery_query_request_count",
    "Number of requests sent to a celery task.",
    ["task"],
    subsystem="django",
)

CELERY_QUERY_DURATION = histogram(
    "celery_query_duration",
    "Database query duration by celery tasks.",
    ["db", "task"],
    unit="seconds",
    subsystem="django",
)

CELERY_QUERY_COUNT = counter(
    "celery_query_count",
    "Number of database queries executed by celery tasks.",
    ["db", "task"],
    subsystem="django",
)

CELERY_DUPLICATE_QUERY_COUNT = counter(
    "celery_duplicate_query_count",
    "Number of duplicate database queries executed by celery tasks.",
    ["db", "task"],
    subsystem="django",
)

#
# Postgres database connection
#

DATABASE_GET_NEW_CONNECTION_HISTOGRAM = histogram(
    "database_get_new_connection_duration",
    "Time it takes to get a new connection to Postgres.",
    ["database_host", "database_port", "database_name", "database_username"],
    unit="seconds",
    subsystem="django",
)

DATABASE_INIT_CONNECTION_STATE_HISTOGRAM = histogram(
    "database_init_connection_state_duration",
    "Time it takes to initialize the connection state.",
    ["database_host", "database_port", "database_name", "database_username"],
    unit="seconds",
    subsystem="django",
)


#
# Signals
#

SIGNAL_DURATION = histogram(
    "signal_duration",
    "Time spent on signals.",
    ["signal"],
    unit="seconds",
    subsystem="django",
)

#
# Middleware
#


MIDDLEWARE_DURATION = histogram(
    "middleware_duration",
    "Time spent on middleware methods.",
    ["middleware", "method"],
    unit="seconds",
    subsystem="django",
)
