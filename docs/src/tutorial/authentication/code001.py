from typing import Annotated, Any

from hattori import NinjaAPI, Response
from hattori.security import django_auth

api = NinjaAPI()


@api.get("/pets", auth=django_auth)
def pets(request) -> Annotated[Response[Any], 200]:
    return Response(200, f"Authenticated user {request.auth}")
