from typing import Annotated, Any

from django.contrib import admin
from django.urls import path

from hattori import NinjaAPI, Response

api = NinjaAPI()


@api.get("/add")
def add(request, a: int, b: int) -> Annotated[Response[Any], 200]:
    return Response(200, {"result": a + b})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
