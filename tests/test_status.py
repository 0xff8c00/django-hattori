from typing import List, Union
import pytest

from hattori import Field, NinjaAPI, Schema, Status
from hattori.responses import codes_2xx, codes_3xx
from hattori.testing import TestClient

# -- Schemas --


class UserOut(Schema):
    id: int
    name: str


class UserOutSub(UserOut):
    extra: str = "default"


class ErrorOut(Schema):
    detail: str


class AliasOut(Schema):
    user_name: str = Field(serialization_alias="userName")


# -- API for basic Status tests --

api = NinjaAPI()


@api.get("/status_dict", response={200: UserOut, 400: ErrorOut})
def status_dict(request):
    return Status(200, {"id": 1, "name": "John"})


@api.get("/status_error", response={200: UserOut, 400: ErrorOut})
def status_error(request):
    return Status(400, {"detail": "bad request"})


@api.get("/status_none", response={204: None})
def status_none(request):
    return Status(204, None)


@api.get("/status_ellipsis", response={200: UserOut, ...: ErrorOut})
def status_ellipsis(request, code: int):
    if code == 200:
        return Status(200, {"id": 1, "name": "John"})
    return Status(code, {"detail": "fallback"})


@api.get("/status_code_groups", response={codes_2xx: UserOut, codes_3xx: ErrorOut})
def status_code_groups(request, code: int):
    if code < 300:
        return Status(code, {"id": 1, "name": "John"})
    return Status(code, {"detail": "redirect"})


@api.get("/status_model_instance", response={200: UserOut})
def status_model_instance(request):
    return Status(200, UserOut(id=1, name="John"))


# -- Tuple deprecation --


@api.get("/tuple_return", response={200: UserOut, 400: ErrorOut})
def tuple_return(request):
    return 200, {"id": 1, "name": "John"}


# -- Skip re-validation --


@api.get("/model_instance", response=UserOut)
def model_instance(request):
    return UserOut(id=1, name="John")


@api.get("/model_subclass", response=UserOut)
def model_subclass(request):
    return UserOutSub(id=1, name="John", extra="bonus")


@api.get("/dict_result", response=UserOut)
def dict_result(request):
    return {"id": 1, "name": "John"}


@api.get("/union_response", response={200: Union[int, UserOut], 400: ErrorOut})
def union_response(request, q: int):
    if q == 0:
        return Status(200, 1)
    return Status(200, UserOut(id=1, name="John"))


@api.get("/list_response", response={200: List[UserOut]})
def list_response(request):
    return Status(200, [{"id": 1, "name": "John"}])


@api.get("/by_alias_response", response=AliasOut, by_alias=True)
def by_alias_response(request):
    return AliasOut(user_name="Alice")


# -- Clients --

client = TestClient(api)


# -- Tests: Status basic --


class TestStatusBasic:
    def test_status_with_dict(self):
        response = client.get("/status_dict")
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "John"}

    def test_status_error_code(self):
        response = client.get("/status_error")
        assert response.status_code == 400
        assert response.json() == {"detail": "bad request"}

    def test_status_none_204(self):
        response = client.get("/status_none")
        assert response.status_code == 204
        assert response.content == b""

    def test_status_ellipsis_200(self):
        response = client.get("/status_ellipsis?code=200")
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "John"}

    def test_status_ellipsis_fallback(self):
        response = client.get("/status_ellipsis?code=500")
        assert response.status_code == 500
        assert response.json() == {"detail": "fallback"}

    def test_status_code_groups_2xx(self):
        response = client.get("/status_code_groups?code=200")
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "John"}

    def test_status_code_groups_201(self):
        response = client.get("/status_code_groups?code=201")
        assert response.status_code == 201
        assert response.json() == {"id": 1, "name": "John"}

    def test_status_code_groups_3xx(self):
        response = client.get("/status_code_groups?code=300")
        assert response.status_code == 300
        assert response.json() == {"detail": "redirect"}

    def test_status_wrapping_model_instance(self):
        response = client.get("/status_model_instance")
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "John"}


# -- Tests: Tuple deprecation --


class TestTupleDeprecation:
    def test_tuple_emits_deprecation_warning(self):
        with pytest.warns(DeprecationWarning, match="deprecated.*Status"):
            client.get("/tuple_return")


# -- Tests: Skip re-validation --


class _ValidateTracker:
    """Tracks calls to Schema.model_validate without breaking it."""

    def __init__(self):
        self.call_count = 0
        self._original_func = Schema.model_validate.__func__  # type: ignore

    def __enter__(self):
        tracker = self
        original = self._original_func

        @classmethod  # type: ignore
        def tracked_validate(cls, *args, **kwargs):
            tracker.call_count += 1
            return original(cls, *args, **kwargs)

        Schema.model_validate = tracked_validate  # type: ignore
        return self

    def __exit__(self, *exc):
        # Remove the override so the inherited BaseModel.model_validate is used again
        if "model_validate" in Schema.__dict__:
            delattr(Schema, "model_validate")


class TestSkipRevalidation:
    """Test that the fast path skips response model_validate for matching model instances."""

    def test_model_instance_skips_validation(self):
        with _ValidateTracker() as t:
            response = client.get("/model_instance")
            assert response.status_code == 200
            assert response.json() == {"id": 1, "name": "John"}
            assert t.call_count == 0

    def test_subclass_skips_validation(self):
        with _ValidateTracker() as t:
            response = client.get("/model_subclass")
            assert response.status_code == 200
            assert response.json() == {"id": 1, "name": "John", "extra": "bonus"}
            assert t.call_count == 0

    def test_dict_goes_through_validation(self):
        with _ValidateTracker() as t:
            response = client.get("/dict_result")
            assert response.status_code == 200
            assert response.json() == {"id": 1, "name": "John"}
            assert t.call_count == 1

    def test_union_no_skip(self):
        with _ValidateTracker() as t:
            response = client.get("/union_response?q=1")
            assert response.status_code == 200
            assert response.json() == {"id": 1, "name": "John"}
            assert t.call_count == 1

    def test_list_no_skip(self):
        with _ValidateTracker() as t:
            response = client.get("/list_response")
            assert response.status_code == 200
            assert response.json() == [{"id": 1, "name": "John"}]
            assert t.call_count == 1

    def test_by_alias_serialization(self):
        response = client.get("/by_alias_response")
        assert response.status_code == 200
        assert response.json() == {"userName": "Alice"}

    def test_status_wrapping_model_skips_validation(self):
        with _ValidateTracker() as t:
            response = client.get("/status_model_instance")
            assert response.status_code == 200
            assert response.json() == {"id": 1, "name": "John"}
            assert t.call_count == 0
