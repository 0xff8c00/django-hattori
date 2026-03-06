import datetime
from typing import Annotated, Any, List

from pydantic import Field

from hattori import Query, Response, Schema


class Filters(Schema):
    limit: int = 100
    offset: int = None
    query: str = None
    category__in: List[str] = Field(None, alias="categories")


@api.get("/filter")
def events(request, filters: Query[Filters]) -> Annotated[Response[Any], 200]:
    return Response(200, {"filters": filters.dict()})
