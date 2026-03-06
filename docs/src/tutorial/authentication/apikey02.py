from typing import Annotated, Any

from hattori import Response
from hattori.security import APIKeyHeader


class ApiKey(APIKeyHeader):
    param_name = "X-API-Key"

    def authenticate(self, request, key):
        if key == "supersecret":
            return key


header_key = ApiKey()


@api.get("/headerkey", auth=header_key)
def apikey(request) -> Annotated[Response[Any], 200]:
    return Response(200, f"Token = {request.auth}")
