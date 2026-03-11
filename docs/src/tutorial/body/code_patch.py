from typing import Annotated

from hattori import PatchDict, Response, Schema


class ItemUpdate(Schema):
    name: str
    description: str | None = None
    price: float
    quantity: int


@api.patch("/items/{item_id}")
def update_item(
    request, item_id: int, payload: PatchDict[ItemUpdate]
) -> Annotated[Response[ItemUpdate], 200]:
    # payload is a dict containing only the fields the client sent
    # e.g. {"price": 9.99} — other fields are excluded
    item = get_item(item_id)
    for key, value in payload.items():
        setattr(item, key, value)
    item.save()
    return Response(200, item)
