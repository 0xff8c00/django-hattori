"""Tests for parameterized generic Schema in responses.

Covers two features:
1. Schema.__class_getitem__ produces clean names for OpenAPI when parameterized
   with Literal values or Enum members.
2. Operation._result_to_response skips re-validation for parameterized generic
   response models (using __pydantic_generic_metadata__ to find the origin type).
"""

from enum import Enum
from typing import Annotated, Generic, Literal, TypeVar

from hattori import NinjaAPI, Response, Schema
from hattori.testing import TestClient

C = TypeVar("C", default=str)


class ErrorResponse(Schema, Generic[C]):
    code: C
    message: str


type ErrResponse[C] = Response[ErrorResponse[C]]


class GetError(Enum):
    NOT_FOUND = "not_found"
    FORBIDDEN = "forbidden"


api = NinjaAPI()


@api.get("/items/{item_id}")
def get_item(
    request, item_id: int
) -> (
    Annotated[Response[dict], 200]
    | Annotated[ErrResponse[Literal[GetError.NOT_FOUND]], 404]
    | Annotated[ErrResponse[Literal[GetError.FORBIDDEN]], 403]
):
    if item_id == 0:
        return Response(404, ErrorResponse(code=GetError.NOT_FOUND, message="Not found"))
    if item_id == -1:
        return Response(403, ErrorResponse(code=GetError.FORBIDDEN, message="Forbidden"))
    return Response(200, {"id": item_id})


@api.get("/string-literal")
def string_literal(
    request,
) -> Annotated[Response[dict], 200] | Annotated[ErrResponse[Literal["custom_error"]], 400]:
    return Response(400, ErrorResponse(code="custom_error", message="Bad"))


client = TestClient(api)


class TestParameterizedGenericResponses:
    def test_enum_literal_404(self):
        response = client.get("/items/0")
        assert response.status_code == 404
        assert response.json() == {"code": "not_found", "message": "Not found"}

    def test_enum_literal_403(self):
        response = client.get("/items/-1")
        assert response.status_code == 403
        assert response.json() == {"code": "forbidden", "message": "Forbidden"}

    def test_success_200(self):
        response = client.get("/items/1")
        assert response.status_code == 200
        assert response.json() == {"id": 1}

    def test_string_literal(self):
        response = client.get("/string-literal")
        assert response.status_code == 400
        assert response.json() == {"code": "custom_error", "message": "Bad"}


class TestSchemaCleanNaming:
    def test_literal_string_naming(self):
        model = ErrorResponse[Literal["not_found"]]
        assert model.__name__ == "ErrorResponse_not_found"
        assert model.__qualname__ == "ErrorResponse_not_found"

    def test_literal_enum_naming(self):
        model = ErrorResponse[Literal[GetError.NOT_FOUND]]
        assert model.__name__ == "ErrorResponse_not_found"

    def test_multiple_literal_values(self):
        model = ErrorResponse[Literal[GetError.NOT_FOUND, GetError.FORBIDDEN]]
        assert model.__name__ == "ErrorResponse_not_found_forbidden"

    def test_plain_type_keeps_default_name(self):
        model = ErrorResponse[str]
        # No Literal values, so Pydantic's default naming is preserved
        assert "ErrorResponse" in model.__name__

    def test_openapi_schema_uses_clean_names(self):
        schema = api.get_openapi_schema()
        defs = schema.get("components", {}).get("schemas", {})
        # Should have clean names like ErrorResponse_not_found, not
        # ErrorResponse_Literal_not_found__
        def_names = set(defs.keys())
        assert "ErrorResponse_not_found" in def_names
        assert "ErrorResponse_forbidden" in def_names

    def test_openapi_responses_reference_clean_names(self):
        schema = api.get_openapi_schema()
        item_get = schema["paths"]["/api/items/{item_id}"]["get"]
        resp_404 = item_get["responses"][404]
        ref = resp_404["content"]["application/json"]["schema"]["$ref"]
        assert ref == "#/components/schemas/ErrorResponse_not_found"
