import time
from datetime import datetime
from typing import Any, cast

from django.utils import timezone

from ..generics.workers import export_worker_busy_state
from ._constants import TASK_HEADERS, TASK_PUBLISH_TIME_HEADER
from ._metrics import (
    TASK_EXECUTION_DELAY,
    TASK_EXECUTION_DURATION,
    TASK_LAST_EXECUTION,
    TASK_PUBLISHED,
)


def _get_headers(task: Any) -> dict[str, Any]:
    """
    Combine all headers in a celery task.
    """

    headers = task.request.headers or {}
    return cast(dict[str, Any], headers.get(TASK_HEADERS, {}))


def _set_headers(
    *, kwarg_headers: dict[str, Any], headers: dict[str, Any]
) -> dict[str, Any]:
    """
    Set metrics-python headers.
    """

    existing_headers = kwarg_headers.copy()

    # Add metrics-python headers if not set.
    existing_headers.setdefault(TASK_HEADERS, {}).update(headers)

    # https://github.com/celery/celery/issues/4875
    #
    # Need to setdefault the inner headers too since other
    # tracing tools (dd-trace-py) also employ this exact
    # workaround and we don't want to break them.
    existing_headers.setdefault("headers", {}).update({TASK_HEADERS: headers})

    return existing_headers


def worker_process_init(**kwargs: Any) -> None:
    # Set the worker as idle on startup
    export_worker_busy_state(busy=False, worker_type="celery")


def before_task_publish(
    sender: str, routing_key: str, *args: Any, **kwargs: Any
) -> None:
    kwarg_headers = kwargs.pop("headers", {})

    message_headers = _set_headers(
        kwarg_headers=kwarg_headers,
        headers={
            TASK_PUBLISH_TIME_HEADER: timezone.now().isoformat(),
        },
    )

    kwargs["headers"] = message_headers

    # Increment the tasks published counter
    TASK_PUBLISHED.labels(task=sender, routing_key=routing_key).inc()


def task_prerun(sender: Any, **kwargs: Any) -> None:
    metrics_python_headers = _get_headers(sender)

    queue: str = getattr(sender, "queue", "default")

    # Set the worker as busy before we start to process a task
    export_worker_busy_state(busy=True, worker_type="celery")

    # Set the task execution delay
    task_published_time = metrics_python_headers.get(TASK_PUBLISH_TIME_HEADER)
    if task_published_time:
        try:
            now = timezone.now()
            task_published = datetime.fromisoformat(task_published_time)
            delay = (now - task_published).total_seconds()

            TASK_EXECUTION_DELAY.labels(task=sender.name, queue=queue).observe(delay)
        except ValueError:
            pass

    # Set the task start time, this is used to measure the task
    # execution duration.
    sender.__metrics_python_start_time = time.perf_counter()


def task_postrun(sender: Any, **kwargs: Any) -> None:
    state: str = kwargs.get("state", "unknown")
    queue: str = getattr(sender, "queue", "default")

    # Set the task execution duration
    task_started_time = getattr(sender, "__metrics_python_start_time", None)
    if task_started_time:
        duration = time.perf_counter() - task_started_time
        TASK_EXECUTION_DURATION.labels(
            task=sender.name, queue=queue, state=state
        ).observe(duration)

    # Set the worker as idle after the task is processed
    export_worker_busy_state(busy=False, worker_type="celery")

    # Update the last executed timestamp
    TASK_LAST_EXECUTION.labels(
        task=sender.name, queue=queue, state=state
    ).set_to_current_time()
