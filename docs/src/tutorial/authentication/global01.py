from typing import Annotated

from hattori import NinjaAPI, Form, Response, Schema
from hattori.security import HttpBearer


class GlobalAuth(HttpBearer):
    def authenticate(self, request, token):
        if token == "supersecret":
            return token


class TokenResponse(Schema):
    token: str


api = NinjaAPI(auth=GlobalAuth())

# @api.get(...)
# def ...
# @api.post(...)
# def ...


@api.post("/token", auth=None)  # < overriding global auth
def get_token(
    request, username: str = Form(...), password: str = Form(...)
) -> Annotated[Response[TokenResponse], 200]:
    if username == "admin" and password == "giraffethinnknslong":
        return Response(200, {"token": "supersecret"})
