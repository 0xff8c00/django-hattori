from typing import Annotated, Any

from hattori import Response
from hattori.security import HttpBasicAuth


class BasicAuth(HttpBasicAuth):
    def authenticate(self, request, username, password):
        if username == "admin" and password == "secret":
            return username


@api.get("/basic", auth=BasicAuth())
def basic(request) -> Annotated[Response[Any], 200]:
    return Response(200, {"httpuser": request.auth})
