from prometheus_client import Counter, Histogram, Summary

from ..constants import NAMESPACE

#
# Cache
#

CACHE_CALL_DURATION = Histogram(
    "cache_call_duration",
    "Cache call duration by method and alias.",
    ["alias", "method"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="django",
)

CACHE_CALL_GETS_DURATION = Histogram(
    "cache_call_gets_duration",
    "Cache call duration for get requests by cache hit, alias and method.",
    ["alias", "method", "hit"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="django",
)

#
# Django view query counts
#

# This counter is used to calculate the average number of
# sql queries executed by a view.
VIEW_QUERY_REQUESTS_COUNT = Counter(
    "view_query_request_count",
    "Number of requests sent to a view.",
    ["method", "view", "status"],
    namespace=NAMESPACE,
    subsystem="django",
)

VIEW_QUERY_DURATION = Histogram(
    "view_query_duration",
    "Database query duration by views.",
    ["db", "method", "view", "status"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="django",
)

VIEW_QUERY_COUNT = Counter(
    "view_query_count",
    "Number of database queries executed by views.",
    ["db", "method", "view", "status"],
    namespace=NAMESPACE,
    subsystem="django",
)

VIEW_DUPLICATE_QUERY_COUNT = Counter(
    "view_duplicate_query_count",
    "Number of duplicate database queries executed by views.",
    ["db", "method", "view", "status"],
    namespace=NAMESPACE,
    subsystem="django",
)


#
# Django management command query counts
#

# This counter is used to calculate the average number of
# sql queries executed by a management comand.
MANAGEMENT_COMMAND_QUERY_REQUESTS_COUNT = Counter(
    "management_command_query_request_count",
    "Number of requests sent to a management command.",
    ["command"],
    namespace=NAMESPACE,
    subsystem="django",
)

MANAGEMENT_COMMAND_QUERY_DURATION = Histogram(
    "management_command_query_duration",
    "Database query duration by management commands.",
    ["db", "command"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="django",
)

MANAGEMENT_COMMAND_QUERY_COUNT = Counter(
    "management_command_query_count",
    "Number of database queries executed by management commands.",
    ["db", "command"],
    namespace=NAMESPACE,
    subsystem="django",
)

MANAGEMENT_COMMAND_DUPLICATE_QUERY_COUNT = Counter(
    "management_command_duplicate_query_count",
    "Number of duplicate database queries executed by management commands.",
    ["db", "command"],
    namespace=NAMESPACE,
    subsystem="django",
)

#
# Django Celery task query counts
#

# This counter is used to calculate the average number of
# sql queries executed by a task.
CELERY_QUERY_REQUESTS_COUNT = Counter(
    "celery_query_request_count",
    "Number of requests sent to a celery task.",
    ["task"],
    namespace=NAMESPACE,
    subsystem="django",
)

CELERY_QUERY_DURATION = Histogram(
    "celery_query_duration",
    "Database query duration by celery tasks.",
    ["db", "task"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="django",
)

CELERY_QUERY_COUNT = Counter(
    "celery_query_count",
    "Number of database queries executed by celery tasks.",
    ["db", "task"],
    namespace=NAMESPACE,
    subsystem="django",
)

CELERY_DUPLICATE_QUERY_COUNT = Counter(
    "celery_duplicate_query_count",
    "Number of duplicate database queries executed by celery tasks.",
    ["db", "task"],
    namespace=NAMESPACE,
    subsystem="django",
)

#
# Postgres database connection
#

DATABASE_GET_NEW_CONNECTION_HISTOGRAM = Histogram(
    "database_get_new_connection_duration",
    documentation="Time it takes to get a new connection to Postgres.",
    labelnames=["database_host", "database_port", "database_name", "database_username"],
    namespace=NAMESPACE,
    subsystem="django",
)

DATABASE_INIT_CONNECTION_STATE_HISTOGRAM = Histogram(
    "database_init_connection_state_duration",
    documentation="Time it takes to initialize the connection state.",
    labelnames=["database_host", "database_port", "database_name", "database_username"],
    namespace=NAMESPACE,
    subsystem="django",
)


#
# Signals
#

SIGNAL_DURATION = Histogram(
    "signal_duration",
    "Time spent on signals.",
    ["signal"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="django",
)

#
# Middleware
#


MIDDLEWARE_DURATION = Histogram(
    "middleware_duration",
    "Time spent on middleware methods.",
    ["middleware", "method"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="django",
)

#
# Management commands
#

MANAGEMENT_COMMAND_DURATION = Summary(
    "management_command_duration",
    "Django management command execution duration.",
    ["command"],
    unit="seconds",
    namespace=NAMESPACE,
    subsystem="django",
)