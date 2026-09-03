from ..config import counter, gauge, histogram

TASK_PUBLISHED = counter(
    "task_published",
    "Number of published tasks.",
    ["task", "routing_key"],
    subsystem="celery",
)

TASK_APPLY_DURATION = histogram(
    "task_apply_duration",
    "Time spent applying the task",
    ["task"],
    unit="seconds",
    subsystem="celery",
)

TASK_EXECUTION_DELAY = histogram(
    "task_execution_delay",
    "Time spent in the messaging queue before a worker starts executing a task",
    ["task", "queue"],
    unit="seconds",
    subsystem="celery",
)

TASK_EXECUTION_DURATION = histogram(
    "task_execution_duration",
    "Time spent executing the task",
    ["task", "queue", "state"],
    unit="seconds",
    subsystem="celery",
)

TASK_LAST_EXECUTION = gauge(
    "task_last_execution",
    "Last time a task was executed",
    ["task", "queue", "state"],
    multiprocess_mode="mostrecent",
    subsystem="celery",
)
