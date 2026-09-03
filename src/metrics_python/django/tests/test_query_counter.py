from typing import Any

import pytest

from metrics_python.django._query_counter import QueryCounter


class FakeConnection:
    def __init__(self, alias: str) -> None:
        self.alias = alias


def context(alias: str = "default") -> dict[str, Any]:
    return {"connection": FakeConnection(alias)}


def execute(sql: Any, params: Any, many: Any, ctx: Any) -> None:
    return None


def run(counter: QueryCounter, sql: str, alias: str = "default") -> None:
    """Every query issued through this helper shares the same call site."""

    counter(execute, sql, None, False, context(alias))


def test_same_sql_from_the_same_stack_is_a_duplicate() -> None:
    counter = QueryCounter()

    for _ in range(3):
        run(counter, "SELECT 1")

    # Three executions of one query, so two of them are repeats.
    assert counter.get_total_duplicate_query_count() == 2
    assert counter.get_total_query_count() == 3


def test_same_sql_from_different_stacks_is_not_a_duplicate() -> None:
    counter = QueryCounter()

    run(counter, "SELECT 1")
    run(counter, "SELECT 1")

    # Same SQL, but the two call sites are on different lines.
    assert counter.get_total_duplicate_query_count() == 0
    assert counter.get_total_query_count() == 2


def test_different_sql_from_the_same_stack_is_not_a_duplicate() -> None:
    counter = QueryCounter()

    for i in range(3):
        run(counter, f"SELECT {i}")

    assert counter.get_total_duplicate_query_count() == 0


def test_duplicates_are_summed_across_call_sites_per_alias() -> None:
    """
    Two distinct call sites both producing duplicates on the same connection
    have to be added together. Keying the result by alias alone used to drop
    every call site but the last.
    """

    counter = QueryCounter()

    for _ in range(3):
        run(counter, "SELECT 1")

    for _ in range(4):
        run(counter, "SELECT 2")

    assert counter.get_total_duplicate_query_count() == 2 + 3
    assert counter.get_total_duplicate_query_count_by_alias() == {"default": 5}


def test_duplicates_are_tracked_per_alias() -> None:
    counter = QueryCounter()

    for _ in range(3):
        run(counter, "SELECT 1", alias="replica")

    for _ in range(2):
        run(counter, "SELECT 1", alias="default")

    assert counter.get_total_duplicate_query_count_by_alias() == {
        "replica": 2,
        "default": 1,
    }


def test_query_and_duration_counts_are_tracked_per_alias() -> None:
    counter = QueryCounter()

    run(counter, "SELECT 1", alias="default")
    run(counter, "SELECT 1", alias="replica")
    run(counter, "SELECT 1", alias="replica")

    assert counter.get_total_query_count_by_alias() == {"default": 1, "replica": 2}
    assert counter.get_total_query_duration_seconds() >= 0.0


def test_nothing_is_recorded_when_observation_is_disabled(
    settings: Any,
) -> None:
    settings.METRICS_PYTHON_OBSERVE_DUPLICATE_QUERIES = False

    counter = QueryCounter()

    for _ in range(3):
        run(counter, "SELECT 1")

    assert counter.get_total_duplicate_query_count() == 0
    assert counter.stack_indexes == {}
    # Queries themselves are still counted.
    assert counter.get_total_query_count() == 3


def test_stacks_are_only_captured_when_printing(settings: Any) -> None:
    """
    Keeping the frames is only needed to format them, and holding stacks for
    every distinct query in a request is not free.
    """

    settings.METRICS_PYTHON_PRINT_DUPLICATE_QUERIES = False

    counter = QueryCounter()
    run(counter, "SELECT 1")

    assert counter.stack_indexes != {}
    assert counter.stacks == []
    assert counter.stack_summaries == []


def test_printing_duplicates_reports_them(
    settings: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    settings.METRICS_PYTHON_PRINT_DUPLICATE_QUERIES = True

    counter = QueryCounter()

    for _ in range(3):
        run(counter, "SELECT 1")

    counter.print_duplicate_queries()

    out = capsys.readouterr().out

    assert "Duplicate queries detected!" in out
    assert "executed 3 times" in out
    assert "Total of 1 duplicate queries" in out
