import ipaddress
import logging

import httpx
from packaging.version import InvalidVersion, Version

from .core.config import settings


async def resolve_country_for_ip(*, ip_address: str) -> str | None:
    """
    Return a country given an IP address.

    The resolution is performed by using the ipinfo.io API.

    Args:
        ip_address (str): IP address to get the country for.

    Returns:
        str | None: A country code or none if the IP does not resolve to a country.
    """
    if not settings.IPINFO_TOKEN:
        logging.error("cannot use ipinfo lookup, IPINFO_TOKEN not set")
        return None

    address = ipaddress.ip_address(address=ip_address)
    if address.is_private:
        return None

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{settings.IPINFO_API_URL}{ip_address}",
            params={"token": settings.IPINFO_TOKEN},
        )

        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logging.error(f"ipinfo lookup failure: {exc.request.url} - {exc}")

        country_code = r.json().get("country_code", None)
        return str(country_code) if country_code else None


def version_strip_micro(*, version: str | None) -> str | None:
    """
    Given a version, return a string with only the major and minor version numbers.

    Args:
        version (str | None): The version to use, if None, it will be returned as is.

    Returns:
        str | None: A  X.Y version with X being the major number and Y the minor number.
    """
    if not version:
        return version

    try:
        parsed = Version(version=version)
        return f"{parsed.major}.{parsed.minor}"
    except InvalidVersion:
        return None
