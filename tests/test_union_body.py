"""Test that Union types containing both generic types and pydantic models
are correctly classified as Body params, not Query params."""

from typing import Dict, Union

from ninja import NinjaAPI, Schema
from ninja.testing import TestClient


class ItemSchema(Schema):
    name: str


api = NinjaAPI()


@api.post("/union-dict-model")
def union_endpoint(request, payload: Union[Dict[str, int], ItemSchema]):
    """Dict is generic but not a collection — only is_pydantic_model catches this."""
    if isinstance(payload, dict):
        return {"type": "dict", "data": payload}
    return {"type": "model", "data": payload.dict()}


client = TestClient(api)


def test_union_with_generic_and_model_is_body():
    """Union[Dict[str, int], ItemSchema] should be treated as Body."""
    response = client.post("/union-dict-model", json={"name": "test"})
    assert response.status_code == 200, response.json()
