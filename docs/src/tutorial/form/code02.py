from typing import Annotated

from hattori import Form, Response, Schema


class Item(Schema):
    name: str
    description: str | None = None
    price: float
    quantity: int


class ItemUpdateResponse(Schema):
    item_id: int
    item: Item
    q: str


@api.post("/items/{item_id}")
def update(
    request, item_id: int, q: str, item: Form[Item]
) -> Annotated[Response[ItemUpdateResponse], 200]:
    return Response(200, {"item_id": item_id, "item": item, "q": q})
