# Django Hattori - Fast Django REST Framework

**Django Hattori** is an opinionated fork of [Django Ninja](https://github.com/vitalik/django-ninja), a web framework for building APIs with **Django** and Python **type hints**.

**Documentation**: [https://0xff8c00.github.io/django-hattori/](https://0xff8c00.github.io/django-hattori/)

*Fast to learn, fast to code, fast to run*

**Key features:**

  - **Easy**: Designed to be easy to use and intuitive.
  - **FAST execution**: Very high performance thanks to [Pydantic](https://pydantic-docs.helpmanual.io) and [async support](docs/docs/guides/async-support.md).
  - **Fast to code**: Type hints and automatic docs lets you focus only on business logic.
  - **Standards-based**: Based on the open standards for APIs: **OpenAPI** (previously known as Swagger) and **JSON Schema**.
  - **Django friendly**: (obviously) has good integration with the Django core and ORM.

---

## Installation

```
pip install django-hattori
```

## Quick Start

Create `api.py` next to your `urls.py`:

```python
from typing import Annotated

from django.contrib.auth.models import User
from hattori import NinjaAPI, Response, Schema
from hattori.security import HttpBearer


api = NinjaAPI()


# --- Schemas ---

class SignupIn(Schema):
    username: str
    password: str

class UserOut(Schema):
    id: int
    username: str

class Error(Schema):
    detail: str


# --- Auth ---

class BearerAuth(HttpBearer):
    def authenticate(self, request, token):
        if token == "supersecret":
            return token


# --- Endpoints ---

@api.post("/signup")
def signup(request, data: SignupIn) -> Annotated[Response[UserOut], 201] | Annotated[Response[Error], 400]:
    if User.objects.filter(username=data.username).exists():
        return Response(400, {"detail": "Username taken"})
    user = User.objects.create_user(username=data.username, password=data.password)
    return Response(201, user)


@api.get("/me", auth=BearerAuth())
def me(request) -> Annotated[Response[UserOut], 200]:
    return Response(200, request.auth)
```

Wire it up in `urls.py`:

```python
from .api import api

urlpatterns = [
    path("api/", api.urls),
]
```

**That's it.** Every status code, request body, and response schema is auto-documented in your OpenAPI spec — no extra configuration needed.

### What you get for free

- **Input validation** — `SignupIn` validates and type-casts the request body
- **Output filtering** — `UserOut` strips fields like `password` from the response
- **Multiple responses** — `201 | 400` union types map directly to OpenAPI response schemas
- **Auth** — `401 Unauthorized` is auto-documented when `auth=` is set
- **422 errors** — validation error responses are added to the schema automatically
- **Interactive docs** — visit `/api/docs` for Swagger UI with everything above

![Swagger UI](docs/docs/img/index-swagger-ui.png)
