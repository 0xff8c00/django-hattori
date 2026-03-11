"""Test that Union types containing both generic types and pydantic models
are correctly classified as Body params, not Query params."""

from typing import Annotated

from hattori import NinjaAPI, Response, Schema
from hattori.testing import TestClient


class ItemSchema(Schema):
    name: str


class UnionResponse(Schema):
    type: str
    data: dict[str, str] | dict[str, int]


api = NinjaAPI()


@api.post("/union-dict-model")
def union_endpoint(
    request, payload: dict[str, int] | ItemSchema
) -> Annotated[Response[UnionResponse], 200]:
    """Dict is generic but not a collection — only is_pydantic_model catches this."""
    if isinstance(payload, dict):
        return Response(200, {"type": "dict", "data": payload})
    return Response(200, {"type": "model", "data": payload.dict()})


client = TestClient(api)


def test_union_with_generic_and_model_is_body():
    """Union[Dict[str, int], ItemSchema] should be treated as Body."""
    response = client.post("/union-dict-model", json={"name": "test"})
    assert response.status_code == 200, response.json()
