import ipaddress
import logging

import httpx

from .core.config import settings


async def resolve_country_for_ip(*, ip_address: str) -> str | None:
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

        country_code = r.json().get("country", None)
        return str(country_code) if country_code else None
