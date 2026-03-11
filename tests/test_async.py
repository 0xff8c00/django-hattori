import asyncio
from typing import Annotated

import pytest

from hattori import NinjaAPI, Response, Schema
from hattori.security import APIKeyQuery
from hattori.testing import TestAsyncClient


class AsyncResult(Schema):
    is_async: bool


class SyncResult(Schema):
    sync: bool


@pytest.mark.asyncio
async def test_asyncio_operations():
    api = NinjaAPI()

    class KeyQuery(APIKeyQuery):
        def authenticate(self, request, key):
            if key == "secret":
                return key

    @api.get("/async", auth=KeyQuery())
    async def async_view(
        request, payload: int
    ) -> Annotated[Response[AsyncResult], 200]:
        await asyncio.sleep(0)
        return Response(200, {"is_async": True})

    @api.post("/async")
    def sync_post_to_async_view(request) -> Annotated[Response[SyncResult], 200]:
        return Response(200, {"sync": True})

    client = TestAsyncClient(api)

    # Actual tests --------------------------------------------------

    # without auth:
    res = await client.get("/async?payload=1")
    assert res.status_code == 401

    # async successful
    res = await client.get("/async?payload=1&key=secret")
    assert res.json() == {"is_async": True}

    # async innvalid input
    res = await client.get("/async?payload=str&key=secret")
    assert res.status_code == 422

    # async call to sync method for path that have async operations
    res = await client.post("/async")
    assert res.json() == {"sync": True}

    # invalid method
    res = await client.put("/async")
    assert res.status_code == 405
