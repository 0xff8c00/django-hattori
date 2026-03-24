from typing import Annotated

from hattori import Response
from hattori.security import APIKeyCookie


class CookieKey(APIKeyCookie):
    def authenticate(self, request, key):
        if key == "supersecret":
            return key


cookie_key = CookieKey()


@api.get("/cookiekey", auth=cookie_key, url_name="apikey_cookie")
def apikey(request) -> Annotated[Response[str], 200]:
    return Response(200, f"Token = {request.auth}")
