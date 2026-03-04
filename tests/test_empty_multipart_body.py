"""Test that empty string POST values don't crash _MultiPartBody parsing."""

from ninja import Body, Form, Router
from ninja.testing import TestClient

router = Router()


@router.post("/empty-body-str")
def empty_body_str(request, name: str = Body(...), tag: str = Form("")):
    return {"name": name, "tag": tag}


client = TestClient(router)


def test_empty_string_body_param():
    """Submitting an empty string for a Body(str) param via multipart should not IndexError."""
    response = client.post("/empty-body-str", POST={"name": "", "tag": "x"})
    assert response.status_code == 200, response.json()
    assert response.json() == {"name": "", "tag": "x"}
