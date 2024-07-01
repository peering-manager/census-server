from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Header, Query
from sqlmodel import select

from ...core.dependencies import SessionDep
from ...enums import CensusRecordEvent
from ...models import CensusRecord, CensusRecordUpdate
from ...notifications import discord_notify
from ...utils import resolve_country_for_ip

router = APIRouter()


@router.post("/", response_model=CensusRecord)
async def create_record(
    *,
    session: SessionDep,
    record: CensusRecordUpdate,
    real_ip: Annotated[str | None, Header(alias="X-Real-IP")] = None,
) -> CensusRecord:
    now = datetime.now(tz=timezone.utc)
    country = await resolve_country_for_ip(ip_address=real_ip) if real_ip else None

    statement = select(CensusRecord).where(
        CensusRecord.deployment_id == record.deployment_id
    )
    results = await session.exec(statement=statement)
    db_record = results.first()

    event: CensusRecordEvent | None = None
    if db_record:
        if (
            db_record.version != record.version
            or db_record.python_version != record.python_version
        ):
            db_record.version = record.version
            db_record.python_version = record.python_version
            db_record.updated_at = now
            db_record.country = country
            event = CensusRecordEvent.UPDATED
    else:
        db_record = CensusRecord(
            deployment_id=record.deployment_id,
            version=record.version,
            python_version=record.python_version,
            country=country,
            created_at=now,
            updated_at=now,
        )
        event = CensusRecordEvent.CREATED

    if event:
        session.add(db_record)
        await session.commit()
        await session.refresh(db_record)

        await discord_notify(event=event, record=db_record)

    return db_record


@router.get("/", response_model=list[CensusRecord])
async def read_records(
    *,
    session: SessionDep,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
) -> Sequence[CensusRecord]:
    result = await session.exec(select(CensusRecord).offset(offset).limit(limit))
    return result.all()