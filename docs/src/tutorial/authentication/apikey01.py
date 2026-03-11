from typing import Annotated

from hattori import Response
from hattori.security import APIKeyQuery
from someapp.models import Client


class ApiKey(APIKeyQuery):
    param_name = "api_key"

    def authenticate(self, request, key):
        try:
            return Client.objects.get(key=key)
        except Client.DoesNotExist:
            pass


api_key = ApiKey()


@api.get("/apikey", auth=api_key)
def apikey(request) -> Annotated[Response[str], 200]:
    assert isinstance(request.auth, Client)
    return Response(200, f"Hello {request.auth}")
