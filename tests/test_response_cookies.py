from typing import Annotated, Any

from django.http import HttpResponse

from hattori import NinjaAPI, Response
from hattori.testing import TestClient

api = NinjaAPI()


@api.get("/test-no-cookies")
def op_no_cookies(request) -> Annotated[Response[Any], 200]:
    return Response(200, {})


@api.get("/test-set-cookie")
def op_set_cookie(request) -> Annotated[Response[Any], 200]:
    response = HttpResponse()
    response.set_cookie(key="sessionid", value="sessionvalue")
    return response  # HttpResponse pass-through


client = TestClient(api)


def test_cookies():
    assert bool(client.get("/test-no-cookies").cookies) is False
    assert "sessionid" in client.get("/test-set-cookie").cookies
