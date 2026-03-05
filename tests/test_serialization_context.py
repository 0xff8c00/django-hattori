from pydantic import model_serializer

from hattori import Router, Schema
from hattori.testing import TestClient


def api_endpoint_test(request):
    return {
        "test1": "foo",
        "test2": "bar",
    }


def test_request_is_passed_in_context_when_supported():
    class SchemaWithCustomSerializer(Schema):
        test1: str
        test2: str

        @model_serializer(mode="wrap")
        def ser_model(self, handler, info):
            assert "request" in info.context
            assert info.context["request"].path == "/test"  # check it is HttRequest
            assert "response_status" in info.context

            return handler(self)

    router = Router()
    router.add_api_operation(
        "/test", ["GET"], api_endpoint_test, response=SchemaWithCustomSerializer
    )

    TestClient(router).get("/test")
