from typing import Annotated, Any

from hattori import Form, Response, Schema


class Item(Schema):
    name: str
    description: str = None
    price: float
    quantity: int


@api.post("/items/{item_id}")
def update(
    request, item_id: int, q: str, item: Form[Item]
) -> Annotated[Response[Any], 200]:
    return Response(200, {"item_id": item_id, "item": item.dict(), "q": q})
