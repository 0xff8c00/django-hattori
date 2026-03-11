from typing import Annotated

from django.contrib import admin
from django.urls import path

from hattori import NinjaAPI, Response, Schema


class AddResult(Schema):
    result: int


api = NinjaAPI()


@api.get("/add")
def add(request, a: int, b: int) -> Annotated[Response[AddResult], 200]:
    return Response(200, {"result": a + b})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
