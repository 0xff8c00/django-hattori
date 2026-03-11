# The goal of this file is to test that mypy "likes" all the combinations of parametrization

from django.http import HttpRequest
from typing_extensions import Annotated

from hattori import Body, BodyEx, NinjaAPI, P, Response, Schema


class Payload(Schema):
    x: int
    y: float
    s: str


api = NinjaAPI()


@api.post("/old_way")
def old_way(
    request: HttpRequest, data: Payload = Body()
) -> Annotated[Response[None], 200]:
    data.s.capitalize()


@api.post("/annotated_way")
def annotated_way(
    request: HttpRequest, data: Annotated[Payload, Body()]
) -> Annotated[Response[None], 200]:
    data.s.capitalize()


@api.post("/new_way")
def new_way(request: HttpRequest, data: Body[Payload]) -> Annotated[Response[None], 200]:
    data.s.capitalize()


@api.post("/new_way_ex")
def new_way_ex(
    request: HttpRequest, data: BodyEx[Payload, P(title="A title")]
) -> Annotated[Response[None], 200]:
    data.s.find("")
