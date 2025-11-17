import time
from typing import Any, Callable

from django.http import HttpRequest, HttpResponse
from ninja.operation import PathView

from ..django._utils import get_request_method
from ._metrics import VIEW_DURATION
from ._utils import get_view_name

NINJA_VIEW = "__metrics_python_django_ninja_view"
NINJA_OPERATION_ID = "__metrics_python_django_ninja_operation_id"


class DjangoNinjaMetricsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        view_start = time.perf_counter()

        response = self.get_response(request)

        if getattr(request, NINJA_VIEW, False):
            view_duration = time.perf_counter() - view_start

            method = get_request_method(request)
            view = get_view_name(
                request=request, operation_id=getattr(request, NINJA_OPERATION_ID, None)
            )
            status = str(response.status_code)

            VIEW_DURATION.labels(method=method, view=view, status=status).observe(
                view_duration
            )

        return response

    def process_view(
        self, request: HttpRequest, view_func: Any, view_args: Any, view_kwargs: Any
    ) -> None:
        """
        Set the __metrics_python_django_ninja_view flag on the request to
        indicate that this is a request to a view served by django-ninja.
        """
        _self = getattr(view_func, "__self__", None)
        _closure = getattr(view_func, "__closure__", None)

        if _self and isinstance(_self, PathView):
            operation = _self._find_operation(request)
            if operation:
                setattr(request, NINJA_VIEW, True)
                setattr(request, NINJA_OPERATION_ID, operation.operation_id)
        elif _closure and isinstance(_closure, tuple) and len(_closure) == 1:
            _cell_content = _closure[0].cell_contents
            if isinstance(_cell_content, PathView):
                operation = _cell_content._find_operation(request)
                if operation:
                    setattr(request, NINJA_VIEW, True)
                    setattr(request, NINJA_OPERATION_ID, operation.operation_id)
