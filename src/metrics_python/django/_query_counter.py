import collections
import contextlib
import hashlib
import sys
import time
import traceback
from logging import getLogger
from types import FrameType
from typing import Any, Generator

from django.db import connections
from django.template import Node

from ..config import metric_enabled, print_duplicate_queries

logger = getLogger(__name__)


def yellow(text: str) -> str:
    return f"\033[33m{text}\033[0m"


def _observe_duplicates() -> bool:
    """
    Walking the stack for every query is only worth it if one of the duplicate
    query counters is actually exported.
    """

    return metric_enabled("django_view_duplicate_query_count") or metric_enabled(
        "django_celery_duplicate_query_count"
    )


class QueryCounter:
    """Query counter."""

    compress_stacktrace = True

    def __init__(self) -> None:
        self.query_count: collections.Counter[str] = collections.Counter()
        self.duration_count: collections.Counter[str] = collections.Counter()

        # Maps the identity of a (stack, sql) pair to its position in
        # stack_summaries and stacks. Hashing the stack keeps this a dict
        # lookup, comparing StackSummary objects against every stack seen so
        # far makes duplicate detection quadratic in the number of queries.
        self.stack_indexes: dict[bytes, int] = {}

        # Only populated when duplicate queries are printed, formatting a stack
        # is the only thing that needs the frames themselves.
        self.stack_summaries: list[tuple[traceback.StackSummary, str]] = []
        self.stacks: list[list[tuple[FrameType, int]]] = []
        self.duplicate_count: collections.Counter[tuple[str, int]] = (
            collections.Counter()
        )

    def __call__(
        self, execute: Any, sql: Any, params: Any, many: Any, context: Any
    ) -> Any:
        alias = context["connection"].alias

        if _observe_duplicates():
            self._observe_stack(alias=alias, sql=sql)

        try:
            start = time.perf_counter_ns()
            return execute(sql, params, many, context)
        finally:
            duration = time.perf_counter_ns() - start

            self.query_count[alias] += 1
            self.duration_count[alias] += duration

    def _observe_stack(self, *, alias: str, sql: str) -> None:
        """
        Record where a query came from. If the same SQL was executed from the
        same stack before, it is a duplicate.

        The stack is identified by a digest of each frame's file, line and
        function. That is what FrameSummary equality compares, locals are only
        populated when a stack is captured with capture_locals, so the digest
        distinguishes exactly the same stacks the comparison used to.
        """

        printing = print_duplicate_queries()

        digest = hashlib.blake2b(digest_size=16)
        frames: list[tuple[FrameType, int]] = []

        # Walk the stack directly rather than with traceback.walk_stack, which
        # starts four frames up to account for being called by
        # StackSummary.extract. Iterated anywhere else it drops the innermost
        # frames, the ones that say where the query actually came from, and
        # returns nothing at all when the stack is shallower than that.
        frame: FrameType | None = sys._getframe().f_back

        while frame is not None:
            code = frame.f_code
            lineno = frame.f_lineno

            digest.update(code.co_filename.encode("utf-8", "replace"))
            digest.update(b"\0")
            digest.update(str(lineno).encode("ascii"))
            digest.update(b"\0")
            digest.update(code.co_name.encode("utf-8", "replace"))
            digest.update(b"\0")

            if printing:
                frames.append((frame, lineno))

            frame = frame.f_back

        digest.update(str(sql).encode("utf-8", "replace"))
        key = digest.digest()

        index = self.stack_indexes.get(key)
        if index is not None:
            self.duplicate_count[(alias, index)] += 1
            return

        self.stack_indexes[key] = len(self.stack_indexes)

        if printing:
            stack = list(reversed(frames))
            self.stacks.append(stack)
            self.stack_summaries.append((traceback.StackSummary.extract(stack), sql))

    def get_total_query_count(self) -> int:
        return self.query_count.total()

    def get_total_query_count_by_alias(self) -> dict[str, int]:
        return self.query_count

    def get_total_query_duration_seconds(self) -> float:
        return self.duration_count.total() / 10.0**9

    def get_total_query_duration_seconds_by_alias(self) -> dict[str, float]:
        return {
            alias: duration / 10.0**9 for alias, duration in self.duration_count.items()
        }

    def get_total_duplicate_query_count(self) -> int:
        return self.duplicate_count.total()

    def get_total_duplicate_query_count_by_alias(self) -> dict[str, int]:
        counts: collections.Counter[str] = collections.Counter()

        for (alias, _), count in self.duplicate_count.items():
            counts[alias] += count

        return dict(counts)

    def print_duplicate_queries(self) -> None:  # noqa: C901
        if not self.duplicate_count:
            return

        print(yellow("\nDuplicate queries detected!"))

        for duplicate, count in self.duplicate_count.items():
            _, stack_index = duplicate
            stack_summary, _ = self.stack_summaries[stack_index]
            stack_raw = self.stacks[stack_index]

            gap = False
            for formatted, (frame, _) in zip(
                stack_summary.format(), stack_raw, strict=True
            ):
                filename = frame.f_code.co_filename
                is_package = "site-packages" in filename
                f_locals = frame.f_locals
                is_template_node = "self" in f_locals and isinstance(
                    f_locals["self"], Node
                )

                if self.compress_stacktrace and is_package and not is_template_node:
                    if not gap:
                        print("  ", end="")
                    print(".", end="")
                    gap = True
                    continue

                if gap:
                    print()

                if is_template_node:
                    node = f_locals["self"]

                    # There is usually multiple stack frames that process the same
                    # template line. For this rendering, we just want to show the
                    # template stack, so we can ignore any frames that have an identical
                    # Node as their predecessor.
                    if frame.f_back:
                        parent_locals = frame.f_back.f_locals
                        parent_is_template = "self" in parent_locals and isinstance(
                            parent_locals["self"], Node
                        )
                        if parent_is_template:
                            parent_node = parent_locals["self"]
                            if parent_node == node:
                                continue

                    print(f'  File "{node.origin.name}", line {node.token.lineno}')
                    print(f"    {node.token.contents}")
                else:
                    print(formatted, end="")

                gap = False

            print(yellow(f"\n^^ The above query was executed {count + 1} times ^^\n"))

        print(
            f"Total of {len(self.duplicate_count)} duplicate queries "
            f"({self.get_total_duplicate_query_count()} executions)"
        )

    @contextlib.contextmanager
    @staticmethod
    def create_counter() -> Generator["QueryCounter", None, None]:
        counter = QueryCounter()

        with contextlib.ExitStack() as stack:
            for alias in connections:
                stack.enter_context(
                    connections[alias].execute_wrapper(counter),
                )

            yield counter

            if print_duplicate_queries():
                counter.print_duplicate_queries()
