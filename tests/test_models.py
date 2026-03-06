from typing import Annotated, Any

import pytest
from pydantic import BaseModel

from hattori import Form, Query, Response, Router
from hattori.testing import TestClient


class SomeModel(BaseModel):
    i: int
    s: str
    f: float


class OtherModel(BaseModel):
    x: int
    y: int


class SelfReference(BaseModel):
    a: int = 123
    sibling: "SelfReference" = None


SelfReference.model_rebuild()


router = Router()


@router.post("/test1")
def view1(request, some: SomeModel) -> Annotated[Response[Any], 200]:
    assert isinstance(some, SomeModel)
    return Response(200, some)


@router.post("/test2")
def view2(request, some: SomeModel, other: OtherModel) -> Annotated[Response[Any], 200]:
    assert isinstance(some, SomeModel)
    assert isinstance(other, OtherModel)
    return Response(200, {"some": some, "other": other})


@router.post("/test3")
def view3(request, some: "SomeModel") -> Annotated[Response[Any], 200]:
    assert isinstance(some, SomeModel)
    return Response(200, some)


@router.post("/test_form")
def view4(request, form: OtherModel = Form(...)) -> Annotated[Response[Any], 200]:
    assert isinstance(form, OtherModel)
    return Response(200, form)


@router.post("/test_query")
def view4query(request, q: OtherModel = Query(...)) -> Annotated[Response[Any], 200]:
    assert isinstance(q, OtherModel)
    return Response(200, q)


@router.post("/selfref")
def view5(request, obj: SelfReference) -> Annotated[Response[Any], 200]:
    assert isinstance(obj, SelfReference)
    return Response(200, obj)


@router.post("/model-default")
def view6(request, obj: OtherModel = None) -> Annotated[Response[Any], 200]:
    assert isinstance(obj, (OtherModel, None.__class__))
    return Response(200, obj)


@router.post("/model-default2")
def view7(request, obj: OtherModel = OtherModel(x=1, y=1)) -> Annotated[Response[Any], 200]:
    assert isinstance(obj, OtherModel)
    return Response(200, obj)


client = TestClient(router)


@pytest.mark.parametrize(
    # fmt: off
    "path,kwargs,expected_response",
    [
        (
            "/test1",
            dict(json={"i": "1", "s": "foo", "f": "1.1"}),
            {"i": 1, "s": "foo", "f": 1.1},
        ),
        (
            "/test2",
            dict(
                json={
                    "some": {"i": "1", "s": "foo", "f": "1.1"},
                    "other": {"x": 1, "y": 2},
                }
            ),
            {"some": {"i": 1, "s": "foo", "f": 1.1}, "other": {"x": 1, "y": 2}},
        ),
        (
            "/test3",
            dict(json={"i": "1", "s": "foo", "f": "1.1"}),
            {"i": 1, "s": "foo", "f": 1.1},
        ),
        (
            "/test_form",
            dict(data={"x": "10000", "y": "20000"}),
            {"x": 10000, "y": 20000},
        ),
        (
            "/test_query?x=5&y=6",
            dict(json=None),
            {"x": 5, "y": 6},
        ),
        (
            "/selfref",
            dict(json={"a": "1"}),
            {"a": 1, "sibling": None},
        ),
        (
            "/selfref",
            dict(json={"a": "1", "sibling": {"a": 2}}),
            {"a": 1, "sibling": {"a": 2, "sibling": None}},
        ),
        (
            "model-default",
            dict(json=None),
            None,
        ),
        (
            "model-default2",
            dict(json=None),
            {"x": 1, "y": 1},
        ),
    ],
    # fmt: on
)
def test_models(path, kwargs, expected_response):
    response = client.post(path, **kwargs)
    assert response.status_code == 200, response.content
    assert response.json() == expected_response


def test_invalid_body():
    response = client.post("/test1", body="invalid")
    assert response.status_code == 400, response.content
    assert response.json() == {
        "detail": "Cannot parse request body",
    }
