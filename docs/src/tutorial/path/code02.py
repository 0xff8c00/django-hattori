from typing import Annotated

from hattori import Response, Schema


class ItemId(Schema):
    item_id: int


@api.get("/items/{item_id}")
def read_item(request, item_id: int) -> Annotated[Response[ItemId], 200]:
    return Response(200, {"item_id": item_id})
