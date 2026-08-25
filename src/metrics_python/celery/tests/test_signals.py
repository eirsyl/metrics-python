from datetime import datetime, timedelta

from celery import Celery
from django.utils import timezone
from prometheus_client import REGISTRY

from metrics_python.celery._constants import TASK_HEADERS, TASK_PUBLISH_TIME_HEADER
from metrics_python.celery._signals import task_prerun

app = Celery("test")


def noop() -> None:
    pass


def _run_prerun(task_name: str, *, published: datetime, eta: str | None = None) -> None:
    """
    Invoke the task_prerun handler for a task published at the given time,
    optionally scheduled with an eta.
    """

    task = app.task(name=task_name)(noop)

    task.push_request(
        headers={TASK_HEADERS: {TASK_PUBLISH_TIME_HEADER: published.isoformat()}},
        eta=eta,
    )

    try:
        task_prerun(task)
    finally:
        task.pop_request()


def _observed_delay(task_name: str) -> float | None:
    value = REGISTRY.get_sample_value(
        "metrics_python_celery_task_execution_delay_seconds_sum",
        {"task": task_name, "queue": "default"},
    )

    return value


def test_execution_delay_measured_from_publish_time_without_eta() -> None:
    now = timezone.now()

    _run_prerun("test.without_eta", published=now - timedelta(seconds=10))

    delay = _observed_delay("test.without_eta")
    assert delay is not None
    assert 9 < delay < 11


def test_execution_delay_excludes_countdown() -> None:
    """
    A task delayed with countdown/eta is not late just because it waited for
    its eta. The delay is measured from the eta, not from publish time.
    """

    now = timezone.now()
    published = now - timedelta(seconds=30)

    _run_prerun(
        "test.with_eta",
        published=published,
        eta=(published + timedelta(seconds=30)).isoformat(),
    )

    delay = _observed_delay("test.with_eta")
    assert delay is not None
    assert delay < 1


def test_execution_delay_counts_waiting_past_the_eta() -> None:
    """
    Waiting after the eta has passed is genuine queue delay.
    """

    now = timezone.now()
    published = now - timedelta(seconds=60)

    _run_prerun(
        "test.late_after_eta",
        published=published,
        eta=(published + timedelta(seconds=30)).isoformat(),
    )

    delay = _observed_delay("test.late_after_eta")
    assert delay is not None
    assert 29 < delay < 31


def test_execution_delay_falls_back_to_publish_time_on_malformed_eta() -> None:
    now = timezone.now()
    published = now - timedelta(seconds=10)

    _run_prerun("test.malformed_eta", published=published, eta="not-a-timestamp")

    delay = _observed_delay("test.malformed_eta")
    assert delay is not None
    assert 9 < delay < 11


def test_execution_delay_is_never_negative() -> None:
    """
    The eta is stamped by the publishing process, so clock skew between it and
    the worker can put the eta slightly in the future. That is not negative
    queue delay.
    """

    now = timezone.now()

    _run_prerun(
        "test.eta_in_future",
        published=now - timedelta(seconds=30),
        eta=(now + timedelta(seconds=5)).isoformat(),
    )

    delay = _observed_delay("test.eta_in_future")
    assert delay == 0
