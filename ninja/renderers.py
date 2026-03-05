from typing import Any, Optional

from django.http import HttpRequest

from ninja.responses import json_dumps

__all__ = ["BaseRenderer", "JSONRenderer"]


class BaseRenderer:
    media_type: Optional[str] = None
    charset: str = "utf-8"

    def render(self, request: HttpRequest, data: Any, *, response_status: int) -> Any:
        raise NotImplementedError("Please implement .render() method")


class JSONRenderer(BaseRenderer):
    media_type = "application/json"

    def render(self, request: HttpRequest, data: Any, *, response_status: int) -> bytes:
        return json_dumps(data)
