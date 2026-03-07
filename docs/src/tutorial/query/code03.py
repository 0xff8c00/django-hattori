from datetime import date
from typing import Annotated, Any

from hattori import Response


@api.get("/example")
def example(
    request, s: str = None, b: bool = None, d: date = None, i: int = None
) -> Annotated[Response[Any], 200]:
    return Response(200, [s, b, d, i])
