from django.http import HttpRequest

from metrics_python.generics.http import sanitize_http_method


def get_request_method(request: HttpRequest) -> str:
    return sanitize_http_method(request.method)


def get_view_name(request: HttpRequest) -> str:
    view_name = "<unnamed view>"
    if hasattr(request, "resolver_match"):
        if request.resolver_match is not None:
            if request.resolver_match.view_name is not None:
                view_name = request.resolver_match.view_name

    return view_name
