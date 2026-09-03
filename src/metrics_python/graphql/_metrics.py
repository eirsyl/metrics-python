from ..config import histogram

OPERATION_DURATION = histogram(
    "operation_duration",
    "Time spent on a GraphQL operation.",
    ["operation_name", "resource", "operation_type", "backend"],
    unit="seconds",
    subsystem="graphql",
)


LIFECYCLE_STEP_DURATION = histogram(
    "lifecycle_step_duration",
    "Time spent on validating or parsing a query.",
    ["lifecycle_step", "backend"],
    unit="seconds",
    subsystem="graphql",
)
