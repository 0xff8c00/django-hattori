import json
from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from typing import Annotated, Any, List, Union

import pytest
from django.http import HttpResponse
from pydantic import BaseModel, ValidationError
from pydantic_core import Url

from hattori import Response, Router
from hattori.responses import JsonResponse
from hattori.testing import TestClient

router = Router()


@router.get("/check_int")
def check_int(request) -> Annotated[Response[int], 200]:
    return Response(200, "1")


@router.get("/check_int2")
def check_int2(request) -> Annotated[Response[int], 200]:
    return Response(200, "str")


class User:
    def __init__(self, id, user_name, password):
        self.id = id
        self.user_name = user_name
        self.password = password


class MyEnum(Enum):
    first = "first"
    second = "second"


def to_camel(string: str) -> str:
    words = string.split("_")
    return words[0].lower() + "".join(word.capitalize() for word in words[1:])


class UserModel(BaseModel):
    id: int
    user_name: str
    # skipping password output to responses

    model_config = dict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


@router.get("/check_model")
def check_model(request) -> Annotated[Response[UserModel], 200]:
    return Response(200, User(1, "John", "Password"))


@router.get("/check_list_model")
def check_list_model(request) -> Annotated[Response[List[UserModel]], 200]:
    return Response(200, [User(1, "John", "Password")])


@router.get("/check_model_alias", by_alias=True)
def check_model_alias(request) -> Annotated[Response[UserModel], 200]:
    return Response(200, User(1, "John", "Password"))


@router.get("/check_union")
def check_union(request, q: int) -> Annotated[Response[Union[int, UserModel]], 200]:
    if q == 0:
        return Response(200, 1)
    if q == 1:
        return Response(200, User(1, "John", "Password"))
    return Response(200, "invalid")


@router.get("/check_set_header")
def check_set_header(request, response: HttpResponse) -> Annotated[Response[Any], 200]:
    response["Cache-Control"] = "no-cache"
    return Response(200, 1)


@router.get("/check_set_cookie")
def check_set_cookie(request, set: bool, response: HttpResponse) -> Annotated[Response[Any], 200]:
    if set:
        response.set_cookie("test", "me")
    return Response(200, 1)


@router.get("/check_del_cookie")
def check_del_cookie(request, response: HttpResponse) -> Annotated[Response[Any], 200]:
    response.delete_cookie("test")
    return Response(200, 1)


client = TestClient(router)


@pytest.mark.parametrize(
    "path,expected_response",
    [
        ("/check_int", 1),
        ("/check_model", {"id": 1, "user_name": "John"}),  # the password is skipped
        (
            "/check_list_model",
            [{"id": 1, "user_name": "John"}],
        ),  # the password is skipped
        ("/check_model", {"id": 1, "user_name": "John"}),  # the password is skipped
        ("/check_model_alias", {"id": 1, "userName": "John"}),  # result is camelCase
        ("/check_union?q=0", 1),
        ("/check_union?q=1", {"id": 1, "user_name": "John"}),
    ],
)
def test_responses(path, expected_response):
    response = client.get(path)
    assert response.status_code == 200, response.content
    assert response.json() == expected_response
    assert response.data == response.data == expected_response  # Ensures cache works


def test_validates():
    with pytest.raises(ValidationError):
        client.get("/check_int2")

    with pytest.raises(ValidationError):
        client.get("/check_union?q=2")


def test_set_header():
    response = client.get("/check_set_header")
    assert response.status_code == 200
    assert response.content == b"1"
    assert response["Cache-Control"] == "no-cache"


def test_set_cookie():
    response = client.get("/check_set_cookie?set=0")
    assert "test" not in response.cookies

    response = client.get("/check_set_cookie?set=1")
    cookie = response.cookies.get("test")
    assert cookie
    assert cookie.value == "me"


def test_del_cookie():
    response = client.get("/check_del_cookie")
    cookie = response.cookies.get("test")
    assert cookie
    assert cookie["expires"] == "Thu, 01 Jan 1970 00:00:00 GMT"
    assert cookie["max-age"] == 0


def test_ipv4address_encoding():
    data = {"ipv4": IPv4Address("127.0.0.1")}
    response = JsonResponse(data)
    response_data = json.loads(response.content)
    assert response_data["ipv4"] == str(data["ipv4"])


def test_ipv6address_encoding():
    data = {"ipv6": IPv6Address("::1")}
    response = JsonResponse(data)
    response_data = json.loads(response.content)
    assert response_data["ipv6"] == str(data["ipv6"])


def test_enum_encoding():
    data = {"enum": MyEnum.first}
    response = JsonResponse(data)
    response_data = json.loads(response.content)
    assert response_data["enum"] == data["enum"].value


def test_pydantic_url():
    data = {"url": Url("https://django-ninja.dev/")}
    response = JsonResponse(data)
    response_data = json.loads(response.content)
    assert response_data == {"url": "https://django-ninja.dev/"}
