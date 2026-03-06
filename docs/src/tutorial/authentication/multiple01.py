from typing import Annotated, Any

from hattori import Response
from hattori.security import APIKeyQuery, APIKeyHeader


class AuthCheck:
    def authenticate(self, request, key):
        if key == "supersecret":
            return key


class QueryKey(AuthCheck, APIKeyQuery):
    pass


class HeaderKey(AuthCheck, APIKeyHeader):
    pass


@api.get("/multiple", auth=[QueryKey(), HeaderKey()])
def multiple(request) -> Annotated[Response[Any], 200]:
    return Response(200, f"Token = {request.auth}")
