from django.http import HttpRequest
from ninja import NinjaAPI

ninja = NinjaAPI()


@ninja.get("/get")
def get(request: HttpRequest) -> None:
    pass
