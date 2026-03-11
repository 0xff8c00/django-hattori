from typing import Annotated

from hattori import Response, Schema
from hattori.security import HttpBasicAuth


class AuthUser(Schema):
    httpuser: str


class BasicAuth(HttpBasicAuth):
    def authenticate(self, request, username, password):
        if username == "admin" and password == "secret":
            return username


@api.get("/basic", auth=BasicAuth())
def basic(request) -> Annotated[Response[AuthUser], 200]:
    return Response(200, {"httpuser": request.auth})
