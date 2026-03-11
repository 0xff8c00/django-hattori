from typing import Annotated

import pytest
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

from hattori import NinjaAPI, Response, Router
from hattori.testing import TestAsyncClient, TestClient
from hattori.throttling import (
    AnonRateThrottle,
    AuthRateThrottle,
    BaseThrottle,
    SimpleRateThrottle,
    UserRateThrottle,
)


@pytest.fixture(autouse=True)
def clear_cache_for_every_case():
    cache.clear()


def test_global_throttling():
    th = AnonRateThrottle("1/s")
    set_throttle_timer(th, 0)

    api = NinjaAPI(throttle=[th])

    @api.get("/check")
    def check(request) -> Annotated[Response[str], 200]:
        return Response(200, "OK")

    client = TestClient(api)

    resp = client.get("/check")
    assert resp.status_code == 200
    assert resp.content == b'"OK"'

    resp = client.get("/check")
    assert resp.status_code == 429
    assert resp.json() == {"detail": "Too many requests."}

    set_throttle_timer(th, 2)
    resp = client.get("/check")
    assert resp.status_code == 200
    assert resp.content == b'"OK"'


def test_router_throttling():
    th = AnonRateThrottle("1/s")
    set_throttle_timer(th, 0)

    api = NinjaAPI()
    router = Router()

    @router.get("/check")
    def check(request) -> Annotated[Response[str], 200]:
        return Response(200, "OK")

    api.add_router("/router", router, throttle=th)

    client = TestClient(api)

    resp = client.get("/router/check")
    assert resp.status_code == 200
    assert resp.content == b'"OK"'

    resp = client.get("/router/check")
    assert resp.status_code == 429
    assert resp.json() == {"detail": "Too many requests."}


def test_router2_throttling():
    "Here we test that child router inherits the throttling from api instance"
    th = AnonRateThrottle("1/s")
    set_throttle_timer(th, 0)

    api = NinjaAPI(throttle=th)
    router = Router()

    @router.get("/check")
    def check(request) -> Annotated[Response[str], 200]:
        return Response(200, "OK")

    api.add_router("/router", router)

    client = TestClient(api)

    resp = client.get("/router/check")
    assert resp.status_code == 200
    assert resp.content == b'"OK"'

    resp = client.get("/router/check")
    assert resp.status_code == 429
    assert resp.json() == {"detail": "Too many requests."}


def test_operation_throttling():
    th = AnonRateThrottle("1/s")
    set_throttle_timer(th, 0)

    api = NinjaAPI()

    @api.get("/check1", throttle=th)
    def check(request) -> Annotated[Response[str], 200]:
        return Response(200, "OK")

    client = TestClient(api)

    resp = client.get("/check1")
    assert resp.status_code == 200
    assert resp.content == b'"OK"'

    resp = client.get("/check1")
    assert resp.status_code == 429
    assert resp.json() == {"detail": "Too many requests."}


@pytest.mark.asyncio
async def test_async_throttling():
    th = AnonRateThrottle("1/s")
    set_throttle_timer(th, 0)

    api = NinjaAPI(throttle=th)

    @api.get("/check-async")
    async def check(request) -> Annotated[Response[str], 200]:
        return Response(200, "OK")

    client = TestAsyncClient(api)

    resp = await client.get("/check-async")
    assert resp.status_code == 200

    resp = await client.get("/check-async")
    assert resp.status_code == 429


# "Unit tests" for the throttling module

_client = TestClient(NinjaAPI())


def build_request(addr="8.8.8.8", x_forwarded_for=None):
    "Creates a mock request with the given address and optional X-Forwarded-For header."
    meta = {"REMOTE_ADDR": addr}
    if x_forwarded_for:
        meta["HTTP_X_FORWARDED_FOR"] = x_forwarded_for
    return _client._build_request("GET", "/", {}, {"META": meta})


def test_throttle_anon():
    th = AnonRateThrottle("1/s")
    set_throttle_timer(th, 0)

    request = build_request()
    request.auth = None

    assert th.allow_request(request) is True
    assert th.wait() == 1.0
    assert th.get_cache_key(request) == "throttle_anon_8.8.8.8"

    # Next should not allow as it's within the same second
    assert th.allow_request(request) is False

    # For auth request it should always allowed
    request.auth = "some"
    assert th.allow_request(request) is True
    assert th.allow_request(request) is True
    assert th.allow_request(request) is True
    assert th.get_cache_key(request) is None


def test_throttle_auth():
    th = AuthRateThrottle("1/s")
    set_throttle_timer(th, 0)

    request = build_request()
    request.auth = None

    assert th.allow_request(request) is True
    assert th.allow_request(request) is False

    request.auth = "some"
    assert th.allow_request(request) is True
    assert th.allow_request(request) is False

    set_throttle_timer(th, 2)
    assert th.allow_request(request) is True

    assert (
        th.get_cache_key(request)
        == "throttle_auth_a6b46dd0d1ae5e86cbc8f37e75ceeb6760230c1ca4ffbcb0c97b96dd7d9c464b"
    )


def test_throttle_user():
    th = UserRateThrottle("1/s")
    set_throttle_timer(th, 0)

    request = build_request()
    request.user.is_authenticated = True
    request.user.pk = 123

    assert th.allow_request(request) is True
    assert th.allow_request(request) is False

    set_throttle_timer(th, 2)
    assert th.allow_request(request) is True

    assert th.get_cache_key(request) == "throttle_user_123"

    # Not authenticated user:
    request.user.is_authenticated = False
    assert th.allow_request(request) is True
    assert th.allow_request(request) is False
    assert (
        th.get_cache_key(request) == "throttle_user_8.8.8.8"
    )  # not authenticated throttled by IP


def test_wait():
    th = AuthRateThrottle("5/m")
    set_throttle_timer(th, 0)

    request = build_request()
    request.auth = None

    for _i in range(5):
        assert th.allow_request(request) is True

    assert th.allow_request(request) is False
    assert th.wait() == 60

    set_throttle_timer(th, 30)
    assert th.allow_request(request) is False
    assert th.wait() == 30

    # Simulating cache expiration/reset
    th.history = []
    # cache.clear()
    set_throttle_timer(th, 0)
    assert th.wait() == 10  # 60s / 6 available

    # Simulating larger history
    th.history = [0] * 10
    th.now = 0
    assert th.wait() is None  # available becomes negative


def test_rate_parser():
    th = SimpleRateThrottle("1/s")
    assert th.parse_rate(None) == (None, None)
    assert th.parse_rate("1/s") == (1, 1)
    assert th.parse_rate("1/sec") == (1, 1)
    assert th.parse_rate("100/10s") == (100, 10)
    assert th.parse_rate("100/10sec") == (100, 10)
    assert th.parse_rate("100/10") == (100, 10)
    assert th.parse_rate("5/m") == (5, 60)
    assert th.parse_rate("5/min") == (5, 60)
    assert th.parse_rate("500/10m") == (500, 600)
    assert th.parse_rate("500/10min") == (500, 600)
    assert th.parse_rate("10/h") == (10, 3600)
    assert th.parse_rate("10/hour") == (10, 3600)
    assert th.parse_rate("1000/2h") == (1000, 7200)
    assert th.parse_rate("1000/2hour") == (1000, 7200)
    assert th.parse_rate("100/d") == (100, 86400)
    assert th.parse_rate("100/day") == (100, 86400)
    assert th.parse_rate("10_000/7d") == (10000, 86400 * 7)
    assert th.parse_rate("10_000/7day") == (10000, 86400 * 7)

    with pytest.raises(ValueError):
        th.parse_rate("42")


def test_proxy_throttle():
    from hattori.conf import settings

    settings.NUM_PROXIES = 0  # instead of None

    th = SimpleRateThrottle("1/s")
    request = build_request(x_forwarded_for=None)
    assert th.get_ident(request) == "8.8.8.8"

    settings.NUM_PROXIES = 0
    request = build_request(x_forwarded_for="8.8.8.8,127.0.0.1")
    assert th.get_ident(request) == "8.8.8.8"

    settings.NUM_PROXIES = 1
    assert th.get_ident(request) == "127.0.0.1"

    settings.NUM_PROXIES = None


def test_base_classes():
    base = BaseThrottle()
    with pytest.raises(NotImplementedError):
        base.allow_request(build_request())
    assert base.wait() is None

    sample = SimpleRateThrottle("1/s")
    with pytest.raises(NotImplementedError):
        sample.allow_request(build_request())

    throttle = AnonRateThrottle()
    with pytest.raises(ImproperlyConfigured):
        throttle.scope = None
        throttle.get_rate()

    sample_scope2 = SimpleRateThrottle("1/s")
    sample_scope2.scope = "scope2"
    with pytest.raises(ImproperlyConfigured):
        sample_scope2.get_rate()


def test_throttle_rates_updated_by_settings_override():
    """
    get_rate() reads from settings lazily, so Django settings overrides
    are respected at runtime.
    """
    from django.test import override_settings

    custom_rates = {"anon": "1/min", "auth": "2/min", "user": "3/min"}
    with override_settings(NINJA_DEFAULT_THROTTLE_RATES=custom_rates):
        from hattori.conf import Settings
        from django.conf import settings as django_settings

        # Reload settings to pick up the override
        import hattori.conf

        hattori.conf.settings = Settings.model_validate(django_settings)

        th = AnonRateThrottle()
        assert th.rate == "1/min"

        th = AuthRateThrottle()
        assert th.rate == "2/min"

        th = UserRateThrottle()
        assert th.rate == "3/min"

    # Restore settings
    hattori.conf.settings = Settings.model_validate(django_settings)


def set_throttle_timer(throttle: BaseThrottle, value: int):
    """
    Explicitly set the timer, overriding time.time()
    """
    throttle.timer = lambda: value
