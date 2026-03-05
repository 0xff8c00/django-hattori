from hattori.conf import settings


def test_default_configuration():
    assert settings.NUM_PROXIES is None
