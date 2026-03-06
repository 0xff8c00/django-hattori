from typing import Annotated, Any, Optional

from hattori import Response, Schema


class Item(Schema):
    name: str
    description: Optional[str] = None
    price: float
    quantity: int


@api.post("/items")
def create(request, item: Item) -> Annotated[Response[Any], 200]:
    return Response(200, item)
