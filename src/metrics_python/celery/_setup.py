import logging
from functools import wraps
from typing import Any

import celery

from ._metrics import TASK_APPLY_DURATION
from ._signals import (
    before_task_publish,
    task_postrun,
    task_prerun,
    worker_process_init,
)

logger = logging.getLogger(__name__)


def setup_celery_metrics() -> None:
    """
    Patch celery to export metrics.
    """

    # Celery signals has logic to prevent duplicate signal handlers,
    # but we keep the patched logic here to prevent issues in the
    # future if we decide to patch additional celery methods.
    if hasattr(celery, "_metrics_python_is_patched"):
        return

    # Connect signals
    celery.signals.worker_process_init.connect(worker_process_init, weak=True)
    celery.signals.before_task_publish.connect(before_task_publish, weak=False)
    celery.signals.task_prerun.connect(task_prerun, weak=True)
    celery.signals.task_postrun.connect(task_postrun, weak=True)

    _patch_apply_async()

    celery._metrics_python_is_patched = True


def _wrap_apply_async(f: Any) -> Any:
    @wraps(f)
    def apply_async(*args: Any, **kwargs: Any) -> Any:
        task = args[0]

        with TASK_APPLY_DURATION.labels(task=task.name).time():
            return f(*args, **kwargs)

    return apply_async


def _patch_apply_async() -> None:
    from celery.app.task import Task

    Task.apply_async = _wrap_apply_async(Task.apply_async)
