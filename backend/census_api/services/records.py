from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..core.config import settings
from ..crud import records as crud
from ..enums import CensusRecordEvent
from ..models import CensusRecord, CensusRecordUpdate
from ..notifications import get_notifiers
from ..utils import resolve_country_for_ip, version_strip_micro


async def process_census_report(
    *, session: AsyncSession, record: CensusRecordUpdate, real_ip: str | None
) -> CensusRecord:
    now = datetime.now(tz=timezone.utc)

    await crud.delete_expired_records(session=session, start_time=now)

    if record.deployment_id in settings.DEPLOYMENT_IDS_TO_IGNORE:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Deployment ID is the same as used in example configuration",
        )

    db_record = await crud.get_record_for_update(
        session=session, deployment_id=record.deployment_id
    )

    event: CensusRecordEvent | None = None
    send_notification = True

    if db_record:
        interval = (
            now - db_record.updated_at.astimezone(tz=timezone.utc)
        ).total_seconds()
        python_version = version_strip_micro(version=record.python_version)

        if interval >= settings.RATE_LIMIT:
            # Only send a notification if something has really changed
            send_notification = (
                db_record.version != record.version
                or db_record.python_version != python_version
            )

            country = (
                await resolve_country_for_ip(ip_address=real_ip) if real_ip else None
            )
            db_record = await crud.update_record(
                session=session,
                db_record=db_record,
                version=record.version,
                python_version=python_version,
                country=country,
                now=now,
            )
            event = CensusRecordEvent.UPDATED
    else:
        country = await resolve_country_for_ip(ip_address=real_ip) if real_ip else None
        try:
            db_record = await crud.create_record(
                session=session,
                deployment_id=record.deployment_id,
                version=record.version,
                python_version=version_strip_micro(version=record.python_version),
                country=country,
                now=now,
            )
        except IntegrityError:
            # Another concurrent request already created this record
            await session.rollback()
            results = await session.exec(
                select(CensusRecord).where(
                    CensusRecord.deployment_id == record.deployment_id
                )
            )
            return results.first()
        event = CensusRecordEvent.CREATED

    if event and send_notification:
        for notifier in get_notifiers():
            await notifier.send(event=event, record=db_record)

    return db_record
