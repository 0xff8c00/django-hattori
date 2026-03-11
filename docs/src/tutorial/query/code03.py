from datetime import date
from typing import Annotated

from hattori import Response


@api.get("/example")
def example(
    request, s: str = None, b: bool = None, d: date = None, i: int = None
) -> Annotated[Response[list[str | bool | date | int | None]], 200]:
    return Response(200, [s, b, d, i])
