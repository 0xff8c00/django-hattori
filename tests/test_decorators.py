from functools import wraps
from typing import Annotated, Any

from hattori import NinjaAPI, Response
from hattori.decorators import decorate_view
from hattori.testing import TestClient


def some_decorator(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args)
        response["X-Decorator"] = "some_decorator"
        return response

    return wrapper


def test_decorator_before():
    api = NinjaAPI()

    @decorate_view(some_decorator)
    @api.get("/before")
    def dec_before(request) -> Annotated[Response[Any], 200]:
        return Response(200, 1)

    client = TestClient(api)
    response = client.get("/before")
    assert response.status_code == 200
    assert response["X-Decorator"] == "some_decorator"


def test_decorator_after():
    api = NinjaAPI()

    @api.get("/after")
    @decorate_view(some_decorator)
    def dec_after(request) -> Annotated[Response[Any], 200]:
        return Response(200, 1)

    client = TestClient(api)
    response = client.get("/after")
    assert response.status_code == 200
    assert response["X-Decorator"] == "some_decorator"


