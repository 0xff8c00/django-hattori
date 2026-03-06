from typing import Annotated, Any

from hattori import Response, Schema


class Item(Schema):
    name: str
    description: str = None
    price: float
    quantity: int


@api.put("/items/{item_id}")
def update(request, item_id: int, item: Item) -> Annotated[Response[Any], 200]:
    return Response(200, {"item_id": item_id, "item": item.dict()})
