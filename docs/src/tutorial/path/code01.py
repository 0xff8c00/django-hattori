from typing import Annotated, Any
from hattori import Response


@api.get("/items/{item_id}")
def read_item(request, item_id) -> Annotated[Response[Any], 200]:
    return Response(200, {"item_id": item_id})
