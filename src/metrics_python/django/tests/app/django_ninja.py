from django.http import HttpRequest
from ninja import NinjaAPI

ninja = NinjaAPI()


@ninja.get("/get")
def get(request: HttpRequest) -> None:
    pass


@ninja.get("/get-operation-id", operation_id="get-operation-id")
def get_operation_id(request: HttpRequest) -> None:
    pass
