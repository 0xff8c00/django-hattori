from typing import Annotated, Any

from hattori import NinjaAPI, Response

api = NinjaAPI()


@api.get("/operation1", operation_id="my_id")
def operation_1(request) -> Annotated[Response[Any], 200]:
    """
    This will be in description
    """
    return Response(200, {"docstrings": True})


@api.get("/operation2", description="description from argument", deprecated=True)
def operation2(request) -> Annotated[Response[Any], 200]:
    return Response(200, {"description": True, "deprecated": True})


@api.get("/operation3", summary="Summary from argument", description="description arg")
def operation3(request) -> Annotated[Response[Any], 200]:
    "This one also has docstring description"
    return Response(200, {"summary": True, "description": "multiple"})


@api.get("/operation4", tags=["tag1", "tag2"])
def operation4(request) -> Annotated[Response[Any], 200]:
    return Response(200, {"tags": True})


@api.get(
    "/operation5",
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "required": ["email"],
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "phone": {"type": "number"},
                            "email": {"type": "string"},
                        },
                    }
                }
            },
            "required": True,
        },
    },
)
def operation5(request) -> Annotated[Response[Any], 200]:
    return Response(200, {"openapi_extra": True})


@api.get("/not-included", include_in_schema=False)
def not_included(request) -> Annotated[Response[Any], 200]:
    return Response(200, True)


schema = api.get_openapi_schema()


def test_schema():
    op1 = schema["paths"]["/api/operation1"]["get"]
    op2 = schema["paths"]["/api/operation2"]["get"]
    op3 = schema["paths"]["/api/operation3"]["get"]
    op4 = schema["paths"]["/api/operation4"]["get"]
    op5 = schema["paths"]["/api/operation5"]["get"]

    assert op1["operationId"] == "my_id"
    assert op2["operationId"] == "test_openapi_params_operation2"
    assert op3["operationId"] == "test_openapi_params_operation3"
    assert op4["operationId"] == "test_openapi_params_operation4"
    assert op5["operationId"] == "test_openapi_params_operation5"

    assert op1["summary"] == "Operation 1"
    assert op2["summary"] == "Operation2"
    assert op3["summary"] == "Summary from argument"
    assert op4["summary"] == "Operation4"
    assert op5["summary"] == "Operation5"

    assert op1["description"] == "This will be in description"

    assert op2["description"] == "description from argument"
    assert op2["deprecated"] is True

    assert op3["description"] == "description arg"

    assert op4["tags"] == ["tag1", "tag2"]

    assert op5["requestBody"] == {
        "content": {
            "application/json": {
                "schema": {
                    "required": ["email"],
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "phone": {"type": "number"},
                        "email": {"type": "string"},
                    },
                }
            }
        },
        "required": True,
    }


def test_not_included():
    assert list(schema["paths"].keys()) == [
        "/api/operation1",
        "/api/operation2",
        "/api/operation3",
        "/api/operation4",
        "/api/operation5",
    ]
    # checking that "/not-included" is not there
