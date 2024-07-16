# metrics-python

> Generic set of metrics for Python applications.

We collect metrics utils in this package to hopefully make a generic package we
can use in other projects in the future.

## Labels

Common labels like app, env, cluster, component, role, etc. is added to the
metrics using the scrape config. Adding these metrics is not a responsibility we
have in the metrics-python package.

## Application info

Some properties from the application is not added as metric labels by default by
the scrape config. One example is the application version. metrics-python has a
util to expose labels like this to Prometheus.

```python
from metrics_python.generics.info import expose_application_info

expose_application_info(version="your-application-version")
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

### Query count and duration in Celery tasks

Database metrics can also be observed in Celery. Execute
`setup_celery_database_metrics` bellow `setup_celery_metrics`,
look into the Celery section of this document for more information.

```python
from metrics_python.django.celery import setup_celery_database_metrics

setup_celery_database_metrics()
```

### Postgres database connection metrics

The `get_new_connection` method in the PostgreSQL database connection
engine can be observed by using a custom connection engine from
metrics-python.

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
