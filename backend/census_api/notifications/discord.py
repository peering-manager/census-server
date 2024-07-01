import logging

import flag
import httpx

from ..core.config import settings
from ..enums import CensusRecordEvent
from ..models import CensusRecord


async def notify(*, event: CensusRecordEvent, record: CensusRecord) -> None:
    if not settings.DISCORD_WEBHOOK_URL:
        logging.info(
            "unable to process discord notification, DISCORD_WEBHOOK_URL is not set"
        )
        return

    match event:
        case CensusRecordEvent.CREATED:
            title = "New instance of Peering Manager recorded"
        case CensusRecordEvent.UPDATED:
            title = "Peering Manager instance updated"
        case _:
            logging.error(
                f"unable to process discord notification for record "
                f"{record} and event {event}"
            )
            return

    if record.country:
        country_flag = flag.flag(countrycode=record.country)
    else:
        country_flag = ":question:"

    webhook_body = {
        "username": settings.DISCORD_WEBHOOK_USERNAME,
        "embeds": [
            {
                "title": title,
                "url": settings.server_host,
                "color": 16230444,
                "fields": [
                    {
                        "name": "Deployment ID",
                        "value": f"`{record.deployment_id}`",
                        "inline": True,
                    },
                    {
                        "name": "Version",
                        "value": f"`{record.version}`",
                        "inline": True,
                    },
                    {
                        "name": "Python version",
                        "value": f"`{record.python_version}`",
                        "inline": True,
                    },
                    {
                        "name": "Country",
                        "value": (f"`{record.country or 'Unknown'}` {country_flag}"),
                        "inline": True,
                    },
                    {
                        "name": "Created at",
                        "value": f"`{record.created_at}`",
                        "inline": True,
                    },
                    {
                        "name": "Updated at",
                        "value": f"`{record.updated_at}`",
                        "inline": True,
                    },
                ],
            }
        ],
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(settings.DISCORD_WEBHOOK_URL, json=webhook_body)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logging.error(f"discord notification failure: {exc.request.url} - {exc}")
            raise exc
