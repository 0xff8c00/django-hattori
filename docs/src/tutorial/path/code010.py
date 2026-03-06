import datetime
from typing import Annotated, Any
from hattori import Response, Schema, Path


class PathDate(Schema):
    year: int
    month: int
    day: int

    def value(self):
        return datetime.date(self.year, self.month, self.day)


@api.get("/events/{year}/{month}/{day}")
def events(request, date: Path[PathDate]) -> Annotated[Response[Any], 200]:
    return Response(200, {"date": date.value()})
