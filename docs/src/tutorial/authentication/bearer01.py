from typing import Annotated

from hattori import Response, Schema
from hattori.security import HttpBearer


class TokenResponse(Schema):
    token: str


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "supersecret":
            return token


@api.get("/bearer", auth=AuthBearer())
def bearer(request) -> Annotated[Response[TokenResponse], 200]:
    return Response(200, {"token": request.auth})
