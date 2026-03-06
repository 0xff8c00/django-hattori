from typing import Annotated, Any

from hattori import Response
from hattori.security import HttpBearer


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "supersecret":
            return token


@api.get("/bearer", auth=AuthBearer())
def bearer(request) -> Annotated[Response[Any], 200]:
    return Response(200, {"token": request.auth})
