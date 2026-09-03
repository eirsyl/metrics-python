# metrics-python

> Generic set of metrics for Python applications.

## Labels

Common labels like app, env, cluster, component, role, etc. is added to the
metrics using the scrape config. Adding these metrics is not a responsibility we
have in the metrics-python package.

## Monitoring of periodic and cron jobs

**metrics-python** is a utility library that leverages the **prometheus-client** to gather and present metrics for Prometheus. As Prometheus operates on a pull-based model rather than a push-based one, collecting metrics from short-lived jobs can be problematic.

While the push-gateway component addresses this issue, it comes with its own set of drawbacks.

Monitoring cron jobs using Prometheus and AlertManager poses additional challenges due to the inability to interpret cron expressions in PromQL.

As a result, **metrics-python** does not support periodic or cron job monitoring.

## Application info

Some properties from the application is not added as metric labels by default by
the scrape config. One example is the application version. metrics-python has a
util to expose labels like this to Prometheus.

```python
from metrics_python.generics.info import expose_application_info

expose_application_info(version="your-application-version")
```

## Exposing metrics

metrics-python can serve a Prometheus endpoint from a background thread.

```python
from metrics_python.prometheus import start_prometheus_background_server

start_prometheus_background_server()
```

| Environment variable | Default | Effect |
| --- | --- | --- |
| `PROMETHEUS_ENABLED` | `false` | Nothing is served unless this is true. |
| `PROMETHEUS_METRICS_PORT` | `8001` | Port to listen on. The `port` argument takes precedence. |
| `PROMETHEUS_MULTIPROC_DIR` | unset | Directory prometheus-client writes its per process files to. Required for multiprocess mode. |

### Multiprocess mode

Applications that fork, which both gunicorn and celery do, have to run
prometheus-client in multiprocess mode. Every process writes its own files into
`PROMETHEUS_MULTIPROC_DIR`, and the endpoint merges them when scraped. Without
it each worker keeps its own counters and a scrape returns whichever worker
happened to answer.

Point `PROMETHEUS_MULTIPROC_DIR` at a writable directory and pass
`multiprocess=True`:

```python
start_prometheus_background_server(multiprocess=True)
```

Files left behind by a previous run are removed on startup, they would
otherwise be merged into the exposition.

Three metrics depend on multiprocess mode being set up correctly:

| Metric | Mode |
| --- | --- |
| `generics_workers_workers_by_state` | `livesum` |
| `generics_info_application_version` | `livemostrecent` |
| `celery_task_last_execution` | `mostrecent` |

The `live` modes stop counting a process once its file has been removed, which
is what `mark_process_dead` does. See the Gunicorn section for where to call it.

`expose_application_info` also writes the `application_version` gauge for this
reason: the `Info` metric it populates is not supported in multiprocess mode.

The `collectors` argument registers extra collectors on the same registry. They
must not use the regular metric classes, prometheus-client would then export
each value twice, once from the collector and once from the multiprocess
directory.

## Configuration

Everything is configured with environment variables. Metrics are created when
the module defining them is imported, and the documented setup calls
`patch_caching()` and `setup_celery_metrics()` from inside `settings.py`, so
Django settings are not available yet at that point.

A variable starting with `METRICS_PYTHON_` that is not recognised is reported
with a warning at startup. A misspelled flag would otherwise silently do
nothing, which is the worst outcome for a switch meant to keep costs down.

### Enabling and disabling metrics

Each metric has a flag, named after the exported metric without the
`metrics_python` prefix and without the unit suffix. So
`metrics_python_django_signal_duration_seconds` is:

```sh
METRICS_PYTHON_DJANGO_SIGNAL_DURATION_ENABLED=false
```

A disabled metric is never registered, so it costs nothing, and the work needed
to produce its value is skipped rather than thrown away.

These four are **disabled by default**, because nothing we could find reads them
and they are not free to produce:

| Metric | Why |
| --- | --- |
| `graphql_lifecycle_step_duration` | Times every parse, validation and resolver. |
| `celery_task_last_execution` | A `mostrecent` gauge, awkward in multiprocess mode. |
| `django_view_duplicate_query_count` | Walks the stack on every query. |
| `django_celery_duplicate_query_count` | Walks the stack on every query. |

Turn one on when you need it:

```sh
METRICS_PYTHON_DJANGO_VIEW_DUPLICATE_QUERY_COUNT_ENABLED=true
```

Before disabling a metric, check what reads it. A dashboard panel goes blank,
but a recording rule that selects the metric will keep evaluating and produce a
wrong result, which is easy to miss when it feeds an SLO.

### Duplicate queries

Duplicate query detection reports queries that were executed more than once from
the same place in the code. It is off by default, see the table above.

Set `METRICS_PYTHON_PRINT_DUPLICATE_QUERIES=true` to also print each duplicate
and the stack that produced it to stdout. That implies counting them, so one
variable is enough when debugging locally.

### Histogram buckets

Every histogram uses the prometheus-client default buckets. Buckets are the
main lever on how many time series the library produces: a histogram costs one
series per bucket per label combination, plus `_sum` and `_count`.

```sh
METRICS_PYTHON_DJANGO_MIDDLEWARE_DURATION_BUCKETS="0.001,0.005,0.025,0.1"
```

`METRICS_PYTHON_DEFAULT_BUCKETS` applies to every histogram without its own
override. The value is a comma separated list of increasing upper bounds in the
metric's unit; the `+Inf` bucket is added automatically. A value that cannot be
parsed is ignored with a warning, so a typo does not stop the application from
starting.

Two things to keep in mind before changing buckets:

- **Every replica of a deployment has to resolve the same buckets.** Prometheus
  aggregates a histogram by summing over `le`, and replicas that disagree
  produce a histogram that cannot be aggregated.
- **Dashboards and recording rules select individual `le` values.** Removing a
  bucket that a query pins makes that query return nothing. Check what is
  selecting the metric before narrowing its buckets.

## ASGI

metrics-python contains an ASGI middleware to measure request/response durations and sizes.

### Starlette

```python
from starlette.middleware import Middleware
from metrics_python.asgi import ASGIMiddleware

app = Starlette(
    middleware=[Middleware(ASGIMiddleware)]
)
```

### fastapi

```python
from metrics_python.asgi import ASGIMiddleware

app = FastAPI()
app.add_middleware(ASGIMiddleware)
```

## Django

### Cache

Cache metrics can be observed by adding `patch_caching()` to your settings file.

```python
from metrics_python.django.cache import patch_caching

patch_caching()
```

### Middleware

The execution of middlewares can be observed by adding `patch_middlewares()` to your settings file.

```python
from metrics_python.django.middleware import patch_middlewares

patch_middlewares()
```

### Signals

The execution of signals can be observed by adding `patch_signals()` to your settings file.

```python
from metrics_python.django.signals import patch_signals

patch_signals()
```

### Views

View processing, request and response sizes can be measured using the MetricsMiddleware.

```python
MIDDLEWARE = [
    ...
    # It is important to place the MetricsMiddleware before the CommonMiddleware.
    "metrics_python.django.middleware.MetricsMiddleware",
    "django.middleware.common.CommonMiddleware",
]
```

### Query count and duration in views

Database query count, duration, and duplicate queries can be observed
by adding the `QueryCountMiddleware`. Add the middleware as early as
possible in the list of middlewares to observe queries executed by
other middlewares.

```python
MIDDLEWARE = [
    ...
    "metrics_python.django.middleware.QueryCountMiddleware",
]
```

Duplicate query detection is off by default, it walks the stack on every
query, see [Duplicate queries](#duplicate-queries) for how to turn it on.

### Query count and duration in Celery tasks

Database metrics can also be observed in Celery. Execute
`setup_celery_database_metrics` bellow `setup_celery_metrics`,
look into the Celery section of this document for more information.

```python
from metrics_python.django.celery import setup_celery_database_metrics

setup_celery_database_metrics()
```

### Postgres database connection metrics

The `get_new_connection` and `init_connection_state` methods in the PostgreSQL
database connection engine can be observed by using a custom connection engine
from metrics-python.

```python
DATABASES = {
    "default": {
        "ENGINE": 'metrics_python.django.postgres_engine',
        ...
    }
}
```

## Celery

To setup Celery monitoring, import and execute `setup_celery_metrics` as early
as possible in your application to connect Celery signals. This is usually done
in the `settings.py` file in Django applications.

```python
from metrics_python.celery import setup_celery_metrics

setup_celery_metrics()
```

## django-api-decorator

To measure request durations to views served by django-api-decorator, add the `DjangoAPIDecoratorMetricsMiddleware`.

```python
MIDDLEWARE = [
    ...
    "metrics_python.django_api_decorator.DjangoAPIDecoratorMetricsMiddleware",
]
```

## django-ninja

To measure request durations to views served by django-ninja, add the `DjangoNinjaMetricsMiddleware`.

```python
MIDDLEWARE = [
    ...
    "metrics_python.django_ninja.DjangoNinjaMetricsMiddleware",
]
```

## GraphQL

### Strawberry

The Prometheus extension needs to be added to the schema to instrument GraphQL
operations.

```python
import strawberry
from metrics_python.graphql.strawberry import PrometheusExtension

schema = strawberry.Schema(
    Query,
    extensions=[
        PrometheusExtension,
    ],
)
```

### Graphene

metrics-python has a Graphene middleware to instrument GraphQL operations. Add
the middleware to Graphene by changing the GRAPHENE config in `settings.py`.

```python
GRAPHENE = {
    ...
    "MIDDLEWARE": ["metrics_python.graphql.graphene.MetricsMiddleware"],
}
```

## Gunicorn

To setup Gunicorn monitoring, add the Prometheus logger (to measure request
durations) and add the worker state signals to the gunicorn config.

```python
from typing import Any

from metrics_python.generics.workers import export_worker_busy_state
from metrics_python.prometheus import mark_process_dead

logger_class = "metrics_python.gunicorn.Prometheus"


def pre_request(worker: Any, req: Any) -> None:
    export_worker_busy_state(worker_type="gunicorn", busy=True)


def post_request(worker: Any, req: Any, environ: Any, resp: Any) -> None:
    export_worker_busy_state(worker_type="gunicorn", busy=False)


def post_fork(server: Any, worker: Any) -> None:
    export_worker_busy_state(worker_type="gunicorn", busy=False)


def child_exit(server: Any, worker: Any) -> None:
    mark_process_dead(worker.pid)
```

### Worker cleanup in multiprocess mode

`child_exit` only matters when running in [multiprocess mode](#multiprocess-mode).
The worker state gauge uses `livesum`, and prometheus-client has no way to tell
that a process has gone: `mark_process_dead` removing the worker's file is what
makes it stop counting. Without the hook a worker that exits leaves its last
busy or idle value behind, and the gauge counts workers that no longer exist.

The `mark_process_dead` from metrics-python does nothing when
`PROMETHEUS_MULTIPROC_DIR` is unset, so the hook is safe to add either way.

This only shows up when workers are replaced while the application is running,
for example with `--max-requests`. If your workers live as long as the process,
nothing accumulates and the gauge is correct either way.

`child_exit` runs in the master process after a worker exits, which is the hook
prometheus-client documents for this.

## Release new version

We use release-please from Google to relese new versions, this is done automatically.
