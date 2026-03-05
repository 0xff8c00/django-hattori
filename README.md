# Django Hattori - Fast Django REST Framework

**Django Hattori** is an opinionated fork of [Django Ninja](https://github.com/vitalik/django-ninja), a web framework for building APIs with **Django** and Python **type hints**.

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
pip install django-ninja
```

## Usage

In your django project next to urls.py create new `api.py` file:

```python
from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/add")
def add(request, a: int, b: int):
    return {"result": a + b}
```

Now go to `urls.py` and add the following:

```python
...
from .api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),  # <---------- !
]
```

**That's it!**

Now you've just created an API that:

 - receives an HTTP GET request at `/api/add`
 - takes, validates and type-casts GET parameters `a` and `b`
 - decodes the result to JSON
 - generates an OpenAPI schema for defined operation

### Interactive API docs

Now go to [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)

You will see the automatic interactive API documentation (provided by [Swagger UI](https://github.com/swagger-api/swagger-ui) or [Redoc](https://github.com/Redocly/redoc)):

![Swagger UI](docs/docs/img/index-swagger-ui.png)
