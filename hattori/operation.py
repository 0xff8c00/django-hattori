import collections.abc
import inspect
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    cast,
    get_args,
    get_origin,
)

import pydantic
from asgiref.sync import async_to_sync, sync_to_async
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseNotAllowed,
    StreamingHttpResponse,
)
from django.http.response import HttpResponseBase
from pydantic import BaseModel
from typing_extensions import Annotated, get_type_hints

from hattori.compatibility.files import FIX_MIDDLEWARE_PATH, need_to_fix_request_files
from hattori.compatibility.util import UNION_TYPES
from hattori.constants import NOT_SET, NOT_SET_TYPE
from hattori.errors import (
    AuthenticationError,
    ConfigError,
    Throttled,
    ValidationErrorContext,
)
from hattori.params.models import TModels
from hattori.responses import Response
from hattori.schema import Schema
from hattori.signature import ViewSignature, is_async
from hattori.streaming import StreamFormat, _StreamAlias, _serialize_item
from hattori.throttling import BaseThrottle
from hattori.utils import is_async_callable

if TYPE_CHECKING:
    from hattori import NinjaAPI  # pragma: no cover

__all__ = ["Operation", "PathView"]


class _ParsedAnnotation:
    __slots__ = ("response_models", "stream_alias")

    def __init__(self) -> None:
        self.response_models: dict[int, Any] = {}
        self.stream_alias: _StreamAlias | None = None


def _resolve_type_alias(tp: Any) -> Any:
    """Resolve Python 3.12+ type aliases (TypeAliasType) to their underlying types."""
    origin = get_origin(tp)
    if origin is None:
        return tp
    if type(origin).__name__ == "TypeAliasType":
        args = get_args(tp)
        type_params = origin.__type_params__
        resolved = origin.__value__
        if type_params and args:
            mapping = dict(zip(type_params, args))
            resolved = _substitute_typevars(resolved, mapping)
        return resolved
    return tp


def _substitute_typevars(tp: Any, mapping: dict) -> Any:
    """Recursively substitute TypeVars in a type according to the mapping."""
    if tp in mapping:
        return mapping[tp]
    origin = get_origin(tp)
    args = get_args(tp)
    # Handle Pydantic models (get_args returns () but metadata has the args)
    if not args and origin is None:
        meta = getattr(tp, "__pydantic_generic_metadata__", None)
        if meta and meta.get("args"):
            origin = meta["origin"]
            args = meta["args"]
    if origin is None or not args:
        return tp
    new_args = tuple(_substitute_typevars(a, mapping) for a in args)
    return origin[new_args] if len(new_args) > 1 else origin[new_args[0]]


def _parse_return_annotation(view_func: Callable) -> _ParsedAnnotation:
    """Extract {status_code: schema_type} from the function's return type annotation.

    Expects return types of the form:
        -> Annotated[Response[Item], 200]
        -> Annotated[Response[Item], 200] | Annotated[Response[Error], 404]
        -> Annotated[Response[JSONL[Item]], 200]  (streaming)
    """
    hints = get_type_hints(view_func, include_extras=True)
    annotation = hints.get("return", inspect.Parameter.empty)

    # If the function has no return annotation, check __wrapped__ (for decorators
    # that don't use functools.wraps)
    if annotation is inspect.Parameter.empty and hasattr(view_func, "__wrapped__"):
        hints = get_type_hints(view_func.__wrapped__, include_extras=True)
        annotation = hints.get("return", inspect.Parameter.empty)

    if annotation is inspect.Parameter.empty:
        raise ConfigError(
            f"Function {view_func.__name__} must have a return type annotation. "
            f"Example: -> Annotated[Response[Item], 200]"
        )

    # Collect all arms of a Union (or just the single annotation)
    origin = get_origin(annotation)
    if origin in UNION_TYPES:
        arms = get_args(annotation)
    else:
        arms = (annotation,)

    parsed = _ParsedAnnotation()
    for arm in arms:
        arm_origin = get_origin(arm)
        if arm_origin is not Annotated:
            raise ConfigError(
                f"Return type annotation for {view_func.__name__} must use "
                f"Annotated[Response[T], status_code]. Got: {arm}"
            )
        arm_args = get_args(arm)
        # arm_args = (Response[Item], 200)
        if len(arm_args) < 2 or not isinstance(arm_args[1], int):
            raise ConfigError(
                f"Return type annotation for {view_func.__name__} must have an int "
                f"status code as second Annotated argument. Got: {arm_args}"
            )

        response_type = arm_args[0]  # Response[Item]
        status_code = arm_args[1]

        # Resolve type aliases (Python 3.12+ `type` statement)
        response_type = _resolve_type_alias(response_type)

        # Extract T from Response[T]
        resp_origin = get_origin(response_type)
        if resp_origin is not Response:
            raise ConfigError(
                f"Return type annotation for {view_func.__name__} must use "
                f"Response[T] inside Annotated. Got: {response_type}"
            )
        resp_args = get_args(response_type)
        if not resp_args:
            raise ConfigError(
                f"Response must be parameterized with a type, e.g. Response[Item]. "
                f"Got bare Response in {view_func.__name__}"
            )

        schema_type = resp_args[0]  # Item or _StreamAlias
        if isinstance(schema_type, _StreamAlias):
            parsed.stream_alias = schema_type
            schema_type = schema_type.item_type
        parsed.response_models[status_code] = schema_type

    return parsed


class Operation:
    def __init__(
        self,
        path: str,
        methods: list[str],
        view_func: Callable,
        *,
        auth: collections.abc.Sequence[Callable]
        | Callable
        | NOT_SET_TYPE
        | None = NOT_SET,
        throttle: BaseThrottle | list[BaseThrottle] | NOT_SET_TYPE = NOT_SET,
        operation_id: str | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        deprecated: bool | None = None,
        by_alias: bool | None = None,
        exclude_unset: bool | None = None,
        exclude_defaults: bool | None = None,
        exclude_none: bool | None = None,
        include_in_schema: bool = True,
        url_name: str | None = None,
        openapi_extra: dict[str, Any] | None = None,
    ) -> None:
        self.is_async = False
        self.path: str = path
        self.methods: list[str] = methods
        self.view_func: Callable = view_func
        self.api: NinjaAPI = cast("NinjaAPI", None)
        self.csrf_exempt: bool = getattr(view_func, "csrf_exempt", False)
        if url_name is not None:
            self.url_name = url_name

        self.auth_param: (
            collections.abc.Sequence[Callable] | Callable | object | None
        ) = auth
        self.auth_callbacks: collections.abc.Sequence[Callable] = []
        self._set_auth(auth)

        if isinstance(throttle, BaseThrottle):
            throttle = [throttle]
        self.throttle_param = throttle
        self.throttle_objects: list[BaseThrottle] = []
        if throttle is not NOT_SET:
            for th in throttle:  # type: ignore
                assert isinstance(
                    th, BaseThrottle
                ), "Throttle should be an instance of BaseThrottle"
                self.throttle_objects.append(th)

        self.signature = ViewSignature(self.path, self.view_func)
        self.models: TModels = self.signature.models

        self.stream_format: type[StreamFormat] | None = None
        self.stream_item_model: type[Schema] | None = None
        self.response_models: dict[Any, Any]

        # Parse response schema from return type annotation
        parsed = _parse_return_annotation(view_func)
        if parsed.stream_alias is not None:
            self.stream_format = parsed.stream_alias.format_cls
        self.response_models = {}
        for status_code, schema_type in parsed.response_models.items():
            if schema_type is type(None):
                self.response_models[status_code] = None
            else:
                self.response_models[status_code] = self._create_response_model(
                    schema_type
                )
        if self.stream_format and self.response_models:
            first_model = next(iter(self.response_models.values()))
            self.stream_item_model = first_model

        self._resp_annotations: dict[int, Any] = {
            id(model): model.model_fields["response"].annotation
            for model in self.response_models.values()
            if model is not None
        }

        if need_to_fix_request_files(methods, self.models):
            raise ConfigError(
                f"Router '{path}' has method(s) {methods}  that require fixing request.FILES. "
                f"Please add '{FIX_MIDDLEWARE_PATH}' to settings.MIDDLEWARE"
            )

        self.operation_id = operation_id
        self.summary = summary or self.view_func.__name__.title().replace("_", " ")
        self.description = description or self.signature.docstring
        self.tags = tags
        self.deprecated = deprecated
        self.include_in_schema = include_in_schema
        self.openapi_extra = openapi_extra

        # Exporting models params
        self.by_alias = by_alias or False
        self.exclude_unset = exclude_unset or False
        self.exclude_defaults = exclude_defaults or False
        self.exclude_none = exclude_none or False

        if hasattr(view_func, "_ninja_contribute_to_operation"):
            # Allow 3rd party code to contribute to the operation behavior
            callbacks: list[Callable] = view_func._ninja_contribute_to_operation
            for callback in callbacks:
                callback(self)

    def clone(self) -> "Operation":
        """
        Create a fresh copy of this operation for binding to an API.

        This method is used when mounting the same router multiple times
        to ensure each mount has independent operation instances.
        """
        # Create instance without calling __init__ to avoid expensive processing
        cloned = object.__new__(self.__class__)

        # Copy all essential attributes
        cloned.is_async = self.is_async
        cloned.path = self.path
        cloned.methods = list(self.methods)
        cloned.view_func = self.view_func
        cloned.api = cast("NinjaAPI", None)  # Will be set during binding
        cloned.csrf_exempt = self.csrf_exempt

        # Copy url_name if it exists
        if hasattr(self, "url_name"):
            cloned.url_name = self.url_name

        # Copy auth settings
        cloned.auth_param = self.auth_param
        cloned.auth_callbacks = list(self.auth_callbacks)

        # Copy throttle settings
        cloned.throttle_param = self.throttle_param
        cloned.throttle_objects = list(self.throttle_objects)

        # Copy signature and models (immutable after creation, safe to share)
        cloned.signature = self.signature
        cloned.models = self.models

        # Copy streaming attributes
        cloned.stream_format = self.stream_format
        cloned.stream_item_model = self.stream_item_model

        # Copy response models (dict copy for isolation)
        cloned.response_models = dict(self.response_models)
        cloned._resp_annotations = self._resp_annotations

        # Copy metadata
        cloned.operation_id = self.operation_id
        cloned.summary = self.summary
        cloned.description = self.description
        cloned.tags = list(self.tags) if self.tags else None
        cloned.deprecated = self.deprecated
        cloned.include_in_schema = self.include_in_schema
        cloned.openapi_extra = dict(self.openapi_extra) if self.openapi_extra else None

        # Copy export model params
        cloned.by_alias = self.by_alias
        cloned.exclude_unset = self.exclude_unset
        cloned.exclude_defaults = self.exclude_defaults
        cloned.exclude_none = self.exclude_none

        # Re-apply run decorators (from decorate_view) to the clone's run method
        # We can't just copy the decorated run because it's bound to the original instance
        if hasattr(self, "_run_decorators") and self._run_decorators:
            cloned._run_decorators = []  # type: ignore[attr-defined]
            for deco in self._run_decorators:
                cloned.run = deco(cloned.run)  # type: ignore
                cloned._run_decorators.append(deco)  # type: ignore[attr-defined]

        return cloned

    def run(self, request: HttpRequest, **kw: Any) -> HttpResponseBase:
        error = self._run_checks(request)
        if error:
            return error
        try:
            temporal_response = self.api.create_temporal_response(request)
            values = self._get_values(request, kw, temporal_response)
            result = self.view_func(request, **values)
            if self.stream_format:
                return self._stream_response(request, result, temporal_response)
            return self._result_to_response(request, result, temporal_response)
        except Exception as e:
            if isinstance(e, TypeError) and "required positional argument" in str(e):
                msg = "Did you fail to use functools.wraps() in a decorator?"
                msg = f"{e.args[0]}: {msg}" if e.args else msg
                e.args = (msg,) + e.args[1:]
            return self.api.on_exception(request, e)

    def _validate_stream_item(
        self, item: Any, request: HttpRequest, ctx: dict[str, Any]
    ) -> str:
        """Validate a single stream item and return serialized JSON string."""
        assert self.stream_item_model is not None
        validated = self.stream_item_model.model_validate(
            {"response": item}, context=ctx
        )

        result = validated.model_dump(
            context=ctx,
            by_alias=self.by_alias,
            exclude_unset=self.exclude_unset,
            exclude_defaults=self.exclude_defaults,
            exclude_none=self.exclude_none,
        )["response"]
        return _serialize_item(result)

    def _stream_response(
        self,
        request: HttpRequest,
        generator: Any,
        temporal_response: HttpResponse,
    ) -> StreamingHttpResponse:
        """Create a StreamingHttpResponse from a sync generator."""
        assert self.stream_format is not None
        fmt = self.stream_format

        ctx = {"request": request, "response_status": 200}

        def content_iter() -> Any:
            for item in generator:
                data = self._validate_stream_item(item, request, ctx)
                yield fmt.format_chunk(data)
            # Copy headers/cookies after generator completes (user may set them inside)
            for key, value in temporal_response.items():
                if key.lower() != "content-type":
                    response[key] = value
            for cookie_name, cookie in temporal_response.cookies.items():
                response.cookies[cookie_name] = cookie

        response = StreamingHttpResponse(
            content_iter(),
            content_type=fmt.media_type,
            status=temporal_response.status_code,
        )
        # Add format-specific headers
        for key, value in fmt.response_headers().items():
            response[key] = value
        return response

    def _set_auth(
        self, auth: collections.abc.Sequence[Callable] | Callable | object | None
    ) -> None:
        if auth is not None and auth is not NOT_SET:
            self.auth_callbacks = (
                auth if isinstance(auth, collections.abc.Sequence) else [auth]
            )

    def _run_checks(self, request: HttpRequest) -> HttpResponse | None:
        "Runs security/throttle checks for each operation"
        # NOTE: if you change anything in this function - do this also in AsyncOperation

        # Set CSRF exempt status on request so auth handlers can check it
        if self.csrf_exempt:
            # _ninja_csrf_exempt is a special flag that tells auth handler to skip CSRF checks
            request._ninja_csrf_exempt = True  # type: ignore

        # auth:
        if self.auth_callbacks:
            error = self._run_authentication(request)
            if error:
                return error

        # Throttling:
        if self.throttle_objects:
            error = self._check_throttles(request)
            if error:
                return error

        return None

    def _run_authentication(self, request: HttpRequest) -> HttpResponse | None:
        for callback in self.auth_callbacks:
            try:
                result = callback(request)
                if inspect.iscoroutine(result):
                    result = async_to_sync(lambda: result)()
            except Exception as exc:
                return self.api.on_exception(request, exc)

            if result is not None:
                request.auth = result  # type: ignore
                return None
        return self.api.on_exception(request, AuthenticationError())

    def _check_throttles(self, request: HttpRequest) -> HttpResponse | None:
        throttle_durations = []
        for throttle in self.throttle_objects:
            if not throttle.allow_request(request):
                throttle_durations.append(throttle.wait())

        if throttle_durations:
            # Filter out `None` values which may happen in case of config / rate
            durations = [
                duration for duration in throttle_durations if duration is not None
            ]

            duration = max(durations, default=None)
            return self.api.on_exception(request, Throttled(wait=duration))  # type: ignore
        return None

    def _result_to_response(
        self, request: HttpRequest, result: Any, temporal_response: HttpResponse
    ) -> HttpResponseBase:
        """
        The protocol for results
         - if HttpResponse - returns as is
         - if Response object - uses status code + value
        """
        if isinstance(result, HttpResponseBase):
            return result

        if not isinstance(result, Response):
            raise ConfigError(
                f"View {self.view_func.__name__} must return a Response object. "
                f"Got: {type(result).__name__}"
            )

        status: int = result.status_code
        result = result.value

        if status in self.response_models:
            response_model = self.response_models[status]
        else:
            # Fall back to range matching: e.g., status 201 matches model for 200
            base_status = (status // 100) * 100
            if base_status in self.response_models:
                response_model = self.response_models[base_status]
            elif Ellipsis in self.response_models:
                response_model = self.response_models[Ellipsis]
            else:
                raise ConfigError(
                    f"Schema for status {status} is not set in response"
                    f" {self.response_models.keys()}"
                )

        temporal_response.status_code = status

        if response_model is None:
            # Empty response.
            return temporal_response

        ctx = {"request": request, "response_status": status}

        # Skip re-validation for pydantic model instances matching the response type.
        # For parameterized generics (e.g. ErrorResponse[Literal["not_found"]]),
        # check against the origin type since isinstance() doesn't work with
        # parameterized generics directly.
        resp_annotation = self._resp_annotations[id(response_model)]
        meta = getattr(resp_annotation, "__pydantic_generic_metadata__", None)
        resp_type = meta["origin"] if meta and meta.get("origin") else resp_annotation
        if (
            resp_annotation is not Any
            and isinstance(resp_type, type)
            and isinstance(result, BaseModel)
            and isinstance(result, resp_type)
        ):
            result = cast(BaseModel, result).model_dump(
                by_alias=self.by_alias,
                exclude_unset=self.exclude_unset,
                exclude_defaults=self.exclude_defaults,
                exclude_none=self.exclude_none,
                context=ctx,
            )
            return self.api.create_response(
                request, result, temporal_response=temporal_response
            )

        validated_object = response_model.model_validate(
            {"response": result}, context=ctx
        )

        result = validated_object.model_dump(
            by_alias=self.by_alias,
            exclude_unset=self.exclude_unset,
            exclude_defaults=self.exclude_defaults,
            exclude_none=self.exclude_none,
            context=ctx,
        )["response"]
        return self.api.create_response(
            request, result, temporal_response=temporal_response
        )

    def _get_values(
        self, request: HttpRequest, path_params: Any, temporal_response: HttpResponse
    ) -> dict[str, Any]:
        values = {}
        error_contexts: list[ValidationErrorContext] = []
        for model in self.models:
            try:
                data = model.resolve(request, self.api, path_params)
                values.update(data)
            except pydantic.ValidationError as e:
                error_contexts.append(
                    ValidationErrorContext(pydantic_validation_error=e, model=model)
                )
        if error_contexts:
            validation_error = self.api.validation_error_from_error_contexts(
                error_contexts
            )
            raise validation_error
        if self.signature.response_arg:
            values[self.signature.response_arg] = temporal_response
        return values

    def _create_response_model(self, response_param: Any) -> type[Schema] | None:
        if response_param is None:
            return None
        attrs = {"__annotations__": {"response": response_param}}
        return type("NinjaResponseSchema", (Schema,), attrs)


class AsyncOperation(Operation):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.is_async = True

    async def run(self, request: HttpRequest, **kw: Any) -> HttpResponseBase:  # type: ignore
        error = await self._run_checks(request)
        if error:
            return error
        try:
            temporal_response = self.api.create_temporal_response(request)
            values = self._get_values(request, kw, temporal_response)
            if self.stream_format:
                result = self.view_func(request, **values)
                return await self._async_stream_response(
                    request, result, temporal_response
                )
            result = await self.view_func(request, **values)
            return self._result_to_response(request, result, temporal_response)
        except Exception as e:
            if isinstance(e, TypeError) and "required positional argument" in str(e):
                msg = "Did you fail to use functools.wraps() in a decorator?"
                msg = f"{e.args[0]}: {msg}" if e.args else msg
                e.args = (msg,) + e.args[1:]
            return self.api.on_exception(request, e)

    async def _async_stream_response(
        self,
        request: HttpRequest,
        generator: Any,
        temporal_response: HttpResponse,
    ) -> StreamingHttpResponse:
        """Create a StreamingHttpResponse from an async generator."""
        assert self.stream_format is not None
        fmt = self.stream_format

        ctx = {"request": request, "response_status": 200}

        async def content_iter() -> Any:
            async for item in generator:
                data = self._validate_stream_item(item, request, ctx)
                yield fmt.format_chunk(data)
            # Copy headers/cookies after generator completes
            for key, value in temporal_response.items():
                if key.lower() != "content-type":
                    response[key] = value
            for cookie_name, cookie in temporal_response.cookies.items():
                response.cookies[cookie_name] = cookie

        response = StreamingHttpResponse(
            content_iter(),
            content_type=fmt.media_type,
            status=temporal_response.status_code,
        )
        for key, value in fmt.response_headers().items():
            response[key] = value
        return response

    async def _run_checks(self, request: HttpRequest) -> HttpResponse | None:  # type: ignore
        "Runs security/throttle checks for each operation"
        # NOTE: if you change anything in this function - do this also in Sync Operation

        # Set CSRF exempt status on request so auth handlers can check it
        if self.csrf_exempt:
            request._ninja_csrf_exempt = True  # type: ignore

        # auth:
        if self.auth_callbacks:
            error = await self._run_authentication(request)
            if error:
                return error

        # Throttling:
        if self.throttle_objects:
            error = self._check_throttles(request)
            if error:
                return error

        return None

    async def _run_authentication(self, request: HttpRequest) -> HttpResponse | None:  # type: ignore
        for callback in self.auth_callbacks:
            try:
                if is_async_callable(callback) or getattr(callback, "is_async", False):
                    cor: collections.abc.Coroutine | None = callback(request)
                    if cor is None:
                        result = None
                    else:
                        result = await cor
                else:
                    result = await sync_to_async(callback)(request)
            except Exception as exc:
                return self.api.on_exception(request, exc)

            if result is not None:
                request.auth = result  # type: ignore
                return None
        return self.api.on_exception(request, AuthenticationError())


class PathView:
    def __init__(self) -> None:
        self.operations: list[Operation] = []
        self._method_map: dict[str, Operation] = {}
        self.is_async = False  # if at least one operation is async - will become True
        self.url_name: str | None = None

    def add_operation(
        self,
        path: str,
        methods: list[str],
        view_func: Callable,
        *,
        auth: collections.abc.Sequence[Callable]
        | Callable
        | NOT_SET_TYPE
        | None = NOT_SET,
        throttle: BaseThrottle | list[BaseThrottle] | NOT_SET_TYPE = NOT_SET,
        operation_id: str | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        deprecated: bool | None = None,
        by_alias: bool | None = None,
        exclude_unset: bool | None = None,
        exclude_defaults: bool | None = None,
        exclude_none: bool | None = None,
        url_name: str | None = None,
        include_in_schema: bool = True,
        openapi_extra: dict[str, Any] | None = None,
    ) -> Operation:
        if url_name:
            self.url_name = url_name

        OperationClass = Operation
        if is_async(view_func) or inspect.isasyncgenfunction(view_func):
            self.is_async = True
            OperationClass = AsyncOperation

        operation = OperationClass(
            path,
            methods,
            view_func,
            auth=auth,
            throttle=throttle,
            operation_id=operation_id,
            summary=summary,
            description=description,
            tags=tags,
            deprecated=deprecated,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            include_in_schema=include_in_schema,
            url_name=url_name,
            openapi_extra=openapi_extra,
        )

        self.operations.append(operation)
        for method in methods:
            self._method_map[method] = operation
        view_func._ninja_operation = operation  # type: ignore

        return operation

    def clone(self) -> "PathView":
        """
        Create a fresh copy of this PathView with cloned operations.

        This method is used when mounting the same router multiple times
        to ensure each mount has independent PathView and Operation instances.
        """
        cloned = PathView()
        cloned.is_async = self.is_async
        cloned.url_name = self.url_name
        cloned.operations = [op.clone() for op in self.operations]
        cloned._method_map = {
            method: op for op in cloned.operations for method in op.methods
        }
        return cloned

    def get_view(self) -> Callable:
        # Create a unique view function for this PathView

        if self.is_async:
            # Create a wrapper for async view
            async def async_view_wrapper(
                request: HttpRequest, *args: Any, **kwargs: Any
            ) -> HttpResponseBase:
                return await self._async_view(request, *args, **kwargs)

            # All django-ninja views are CSRF exempt at Django middleware level
            # Cookie-based auth (APIKeyCookie) handles CSRF checking separately
            async_view_wrapper.csrf_exempt = True  # type: ignore

            return async_view_wrapper
        else:
            # Create a wrapper for sync view
            def sync_view_wrapper(
                request: HttpRequest, *args: Any, **kwargs: Any
            ) -> HttpResponseBase:
                return self._sync_view(request, *args, **kwargs)

            # All django-ninja views are CSRF exempt at Django middleware level
            # Cookie-based auth (APIKeyCookie) handles CSRF checking separately
            sync_view_wrapper.csrf_exempt = True  # type: ignore

            return sync_view_wrapper

    def _sync_view(self, request: HttpRequest, *a: Any, **kw: Any) -> HttpResponseBase:
        operation = self._find_operation(request)
        if operation is None:
            return self._not_allowed()
        return operation.run(request, *a, **kw)

    async def _async_view(
        self, request: HttpRequest, *a: Any, **kw: Any
    ) -> HttpResponseBase:
        operation = self._find_operation(request)
        if operation is None:
            return self._not_allowed()
        if operation.is_async:
            return await cast(AsyncOperation, operation).run(request, *a, **kw)
        return await sync_to_async(operation.run)(request, *a, **kw)

    def _find_operation(self, request: HttpRequest) -> Operation | None:
        return self._method_map.get(request.method)

    def _not_allowed(self) -> HttpResponse:
        return HttpResponseNotAllowed(
            self._method_map.keys(), content=b"Method not allowed"
        )
