from typing import Annotated, Optional

from hattori import NinjaAPI, Response, Schema
from hattori.testing import TestClient

api = NinjaAPI()


class SomeResponse(Schema):
    field1: Optional[int] = 1
    field2: Optional[str] = "default value"
    field3: Optional[int] = None


@api.get("/test-no-params")
def op_no_params(request) -> Annotated[Response[SomeResponse], 200]:
    return Response(200, {})  # should set defaults from schema


@api.get("/test-unset", exclude_unset=True)
def op_exclude_unset(request) -> Annotated[Response[SomeResponse], 200]:
    return Response(200, {"field3": 10})


@api.get("/test-defaults", exclude_defaults=True)
def op_exclude_defaults(request) -> Annotated[Response[SomeResponse], 200]:
    # changing only field1
    return Response(200, {"field1": 3, "field2": "default value"})


@api.get("/test-none", exclude_none=True)
def op_exclude_none(request) -> Annotated[Response[SomeResponse], 200]:
    # setting field1 to None to exclude
    return Response(200, {"field1": None, "field2": "default value"})


client = TestClient(api)


def test_arguments():
    assert client.get("/test-no-params").json() == {
        "field1": 1,
        "field2": "default value",
        "field3": None,
    }
    assert client.get("/test-unset").json() == {"field3": 10}
    assert client.get("/test-defaults").json() == {"field1": 3}
    assert client.get("/test-none").json() == {"field2": "default value"}
