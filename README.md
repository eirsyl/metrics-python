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

## Configuration

### Django settings

The Django integration reads two settings. Both are optional.

| Setting | Default | Effect |
| --- | --- | --- |
| `METRICS_PYTHON_OBSERVE_DUPLICATE_QUERIES` | `True` | Count duplicate queries on `metrics_python_django_view_duplicate_query_count_total` and `metrics_python_django_celery_duplicate_query_count_total`. |
| `METRICS_PYTHON_PRINT_DUPLICATE_QUERIES` | `False` | Print duplicate queries and the stack that produced them to stdout. Intended for local debugging, and has no effect unless the setting above is also on. |

Duplicate query detection walks the stack on every query and compares it against
every stack already seen in the same request, so it is not free. Turn
`METRICS_PYTHON_OBSERVE_DUPLICATE_QUERIES` off if you do not use the duplicate
query metrics:

```python
METRICS_PYTHON_OBSERVE_DUPLICATE_QUERIES = False
```

### Histogram buckets

Every histogram uses the prometheus-client default buckets. They can be tuned
per metric with environment variables, which is the main lever on how many time
series the library produces: a histogram costs one series per bucket per label
combination, plus `_sum` and `_count`.

The variable name is the exported metric name without the `metrics_python`
prefix and without the unit suffix, upper cased. So
`metrics_python_django_middleware_duration_seconds` is configured with:

```sh
METRICS_PYTHON_BUCKETS_DJANGO_MIDDLEWARE_DURATION="0.001,0.005,0.025,0.1"
```

`METRICS_PYTHON_BUCKETS_DEFAULT` applies to every histogram that has no metric
specific override. The value is a comma separated list of increasing upper
bounds in the metric's unit; the `+Inf` bucket is added automatically. A value
that cannot be parsed is ignored with a warning, so a typo does not stop the
application from starting.

Buckets are resolved when the metric is created, which happens at import time.
Environment variables are therefore the only supported configuration, Django
settings are not available yet at that point.

Two things to keep in mind before changing buckets:

- **Every replica of a deployment has to resolve the same buckets.** Prometheus
  aggregates a histogram by summing over `le`, and replicas that disagree
  produce a histogram that cannot be aggregated.
- **Dashboards and recording rules select individual `le` values.** Removing a
  bucket that a query pins makes that query return nothing, which is easy to
  miss when the query feeds an SLO. Check what is selecting the metric before
  narrowing its buckets.

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

Duplicate query detection is on by default and adds work to every query, see
[Django settings](#django-settings) for how to turn it off.

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
from metrics_python.generics.workers import export_worker_busy_state

logger_class = "metrics_python.gunicorn.Prometheus"

def pre_request(worker: Any, req: Any) -> None:
    export_worker_busy_state(worker_type="gunicorn", busy=True)


def post_request(worker: Any, req: Any, environ: Any, resp: Any) -> None:
    export_worker_busy_state(worker_type="gunicorn", busy=False)


def post_fork(server: Any, worker: Any) -> None:
    export_worker_busy_state(worker_type="gunicorn", busy=False)
```

## Release new version

We use release-please from Google to relese new versions, this is done automatically.
