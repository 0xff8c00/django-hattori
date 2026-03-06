from typing import Annotated, Any

from hattori import Form, Response, Schema


class Item(Schema):
    name: str
    description: str = None
    price: float
    quantity: int


@api.post("/items")
def create(request, item: Form[Item]) -> Annotated[Response[Any], 200]:
    return Response(200, item)
