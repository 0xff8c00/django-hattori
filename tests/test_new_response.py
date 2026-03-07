"""Test the new Response[T] return type annotation pattern."""

from typing import Annotated

from hattori import NinjaAPI, Response, Schema
from hattori.testing import TestClient


class Item(Schema):
    name: str
    price: float


class Error(Schema):
    message: str


api = NinjaAPI()


@api.get("/items")
def list_items(request) -> Annotated[Response[list[Item]], 200]:
    return Response(200, [Item(name="Sword", price=9.99)])


@api.get("/items/{item_id}")
def get_item(
    request, item_id: int
) -> Annotated[Response[Item], 200] | Annotated[Response[Error], 404]:
    if item_id == 0:
        return Response(404, Error(message="not found"))
    return Response(200, Item(name="Sword", price=9.99))


@api.delete("/items/{item_id}")
def delete_item(request, item_id: int) -> Annotated[Response[None], 204]:
    return Response(204, None)


client = TestClient(api)


def test_list_items():
    response = client.get("/items")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Sword"


def test_get_item_success():
    response = client.get("/items/1")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Sword"


def test_get_item_not_found():
    response = client.get("/items/0")
    assert response.status_code == 404
    data = response.json()
    assert data["message"] == "not found"


def test_delete_item():
    response = client.delete("/items/1")
    assert response.status_code == 204


def test_openapi_schema():
    schema = api.get_openapi_schema()
    # Check /items GET response
    items_get = schema["paths"]["/api/items"]["get"]
    assert 200 in items_get["responses"]

    # Check /items/{item_id} GET responses
    item_get = schema["paths"]["/api/items/{item_id}"]["get"]
    assert 200 in item_get["responses"]
    assert 404 in item_get["responses"]

    # Check /items/{item_id} DELETE response
    item_delete = schema["paths"]["/api/items/{item_id}"]["delete"]
    assert 204 in item_delete["responses"]
