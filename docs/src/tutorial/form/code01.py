from typing import Annotated

from hattori import Form, Response, Schema


class Item(Schema):
    name: str
    description: str | None = None
    price: float
    quantity: int


@api.post("/items")
def create(request, item: Form[Item]) -> Annotated[Response[Item], 200]:
    return Response(200, item)
