from datetime import timedelta
from decimal import Decimal
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from typing import Any, FrozenSet, Generic, TypeVar

import orjson
from django.http import HttpResponse
from django.utils.duration import duration_iso_string
from django.utils.functional import Promise
from pydantic import BaseModel
from pydantic_core import Url

__all__ = [
    "Response",
    "JsonResponse",
    "Status",
    "json_default",
    "json_dumps",
    "json_loads",
    "JSON_OPT",
    "codes_1xx",
    "codes_2xx",
    "codes_3xx",
    "codes_4xx",
    "codes_5xx",
]

JSON_OPT = orjson.OPT_UTC_Z | orjson.OPT_NON_STR_KEYS

T = TypeVar("T")


class Response(Generic[T]):
    """Typed API response with explicit status code.

    Usage::

        from typing import Annotated
        from hattori import Response

        @api.get("/items/{id}")
        def get_item(request, id: int) -> Annotated[Response[Item], 200] | Annotated[Response[Error], 404]:
            if not found:
                return Response(404, Error(message="not found"))
            return Response(200, item)
    """

    __slots__ = ("status_code", "value")

    def __init__(self, status_code: int, value: T) -> None:
        self.status_code = status_code
        self.value = value


class Status:
    """Return a response with an explicit HTTP status code.

    Usage:
        return Status(200, {"key": "value"})
        return Status(204, None)
    """

    __slots__ = ("status_code", "value")

    def __init__(self, status_code: int, value: Any):
        self.status_code = status_code
        self.value = value


def json_default(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if isinstance(obj, Url):
        return str(obj)
    if isinstance(obj, (IPv4Address, IPv4Network, IPv6Address, IPv6Network)):
        return str(obj)
    if isinstance(obj, timedelta):
        return duration_iso_string(obj)
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, Promise):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def json_dumps(data: Any) -> bytes:
    return orjson.dumps(data, default=json_default, option=JSON_OPT)


def json_loads(data: Any) -> Any:
    return orjson.loads(data)


class JsonResponse(HttpResponse):
    def __init__(self, data: Any, **kwargs: Any) -> None:
        kwargs.setdefault("content_type", "application/json")
        super().__init__(content=json_dumps(data), **kwargs)


def resp_codes(from_code: int, to_code: int) -> FrozenSet[int]:
    return frozenset(range(from_code, to_code + 1))


# most common http status codes
codes_1xx = resp_codes(100, 101)
codes_2xx = resp_codes(200, 206)
codes_3xx = resp_codes(300, 308)
codes_4xx = resp_codes(400, 412) | frozenset({416, 418, 425, 429, 451})
codes_5xx = resp_codes(500, 504)
