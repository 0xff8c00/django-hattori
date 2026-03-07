from typing import Annotated, Any

from hattori import NinjaAPI, Form, Response
from hattori.security import HttpBearer


class GlobalAuth(HttpBearer):
    def authenticate(self, request, token):
        if token == "supersecret":
            return token


api = NinjaAPI(auth=GlobalAuth())

# @api.get(...)
# def ...
# @api.post(...)
# def ...


@api.post("/token", auth=None)  # < overriding global auth
def get_token(
    request, username: str = Form(...), password: str = Form(...)
) -> Annotated[Response[Any], 200]:
    if username == "admin" and password == "giraffethinnknslong":
        return Response(200, {"token": "supersecret"})
