_known_methods = [
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "DELETE",
    "TRACE",
    "OPTIONS",
    "CONNECT",
    "PATCH",
]


def sanitize_http_method(method: str) -> str:
    """
    Make sure the method is known, we do this to make sure
    rouge clients can't generate a large set of metrics by
    providing random methods.
    This method either returns valid method names from
    _known_methods or UNKNOWN.
    """

    method = method.upper()

    if method in _known_methods:
        return method

    return "<invalid method>"
