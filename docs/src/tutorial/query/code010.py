from typing import Annotated

from hattori import Query, Response, Schema


class Filters(Schema):
    limit: int = 100
    offset: int | None = None
    query: str | None = None
    categories: list[str] | None = None


class FilterResponse(Schema):
    filters: Filters


@api.get("/filter")
def events(request, filters: Query[Filters]) -> Annotated[Response[FilterResponse], 200]:
    return Response(200, {"filters": filters})
