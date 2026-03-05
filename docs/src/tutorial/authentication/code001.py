from hattori import NinjaAPI
from hattori.security import django_auth

api = NinjaAPI()


@api.get("/pets", auth=django_auth)
def pets(request):
    return f"Authenticated user {request.auth}"
