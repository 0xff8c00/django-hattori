# Tutorial - Handling Responses

## Define a response Schema

**Django Ninja** allows you to define the schema of your responses both for validation and documentation purposes.

We'll create a third operation that will return information about the current Django user.

```python
from typing import Annotated
from hattori import Response, Schema

class UserSchema(Schema):
    username: str
    is_authenticated: bool
    # Unauthenticated users don't have the following fields, so provide defaults.
    email: str = None
    first_name: str = None
    last_name: str = None

@api.get("/me")
def me(request) -> Annotated[Response[UserSchema], 200]:
    return Response(200, request.user)
```

This will convert the Django `User` object into a dictionary of only the defined fields.

### Multiple response types

Let's return a different response if the current user is not authenticated.

```python hl_lines="1-2 4-8 10-11 13-16"
from typing import Annotated
from hattori import Response, Schema

class UserSchema(Schema):
    username: str
    email: str
    first_name: str
    last_name: str

class Error(Schema):
    message: str

@api.get("/me")
def me(request) -> Annotated[Response[UserSchema], 200] | Annotated[Response[Error], 403]:
    if not request.user.is_authenticated:
        return Response(403, {"message": "Please sign in first"})
    return Response(200, request.user)
```

As you see, you define multiple response types using union (`|`) type annotations, and return `Response(status_code, value)` objects to specify the HTTP status code and data.

!!! success

    That concludes the tutorial! Check out the **Other Tutorials** or the **How-to Guides** for more information.