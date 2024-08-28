from django.urls import path

from .app.django_ninja import ninja
from .app.view import get

urlpatterns = [
    path("ninja/", ninja.urls),
    path("get", get),
]
