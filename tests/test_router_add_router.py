from typing import Annotated, Any

from hattori import NinjaAPI, Response, Router
from hattori.testing import TestClient

router = Router()


@router.get("/")
def op(request) -> Annotated[Response[Any], 200]:
    return Response(200, True)


def test_add_router_with_string_path():
    main_router = Router()
    main_router.add_router("sub", "tests.test_router_add_router.router")

    api = NinjaAPI()
    api.add_router("main", main_router)

    client = TestClient(api)

    assert client.get("/main/sub/").status_code == 200
