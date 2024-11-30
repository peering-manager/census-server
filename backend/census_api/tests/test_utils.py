import re

import pytest
from pytest_httpx import HTTPXMock

from census_api.core.config import settings
from census_api.utils import resolve_country_for_ip, version_strip_micro


@pytest.mark.parametrize(
    ("ip_address", "country"), [("45.154.62.1", "FR"), ("2001:678:794::1", "FR")]
)
async def test_resolve_country_for_ip(
    httpx_mock: HTTPXMock, ip_address: str, country: str
):
    if country is None:
        assert not await resolve_country_for_ip(ip_address=ip_address)

    settings.IPINFO_TOKEN = "abcdef0123456789"
    httpx_mock.add_response(
        url=re.compile(f"{settings.IPINFO_API_URL}.*"),
        json={"country": country},
    )

    assert await resolve_country_for_ip(ip_address=ip_address) == country


@pytest.mark.parametrize(
    ("version", "result"),
    [(None, None), ("1", "1.0"), ("1.2", "1.2"), ("1.2.3", "1.2"), ("abcdef", None)],
)
def test_version_strip_micro(version: str, result: str):
    assert version_strip_micro(version=version) == result
