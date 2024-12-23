from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, status
from sqlmodel import select, text

from ...core.config import settings
from ...core.dependencies import SessionDep
from ...enums import CensusRecordEvent
from ...models import CensusRecord, CensusRecordUpdate, CensusSummaries, CensusSummary
from ...notifications import discord_notify
from ...utils import delete_expired_records, resolve_country_for_ip, version_strip_micro

router = APIRouter()


@router.post("/", response_model=CensusRecord)
async def create_record(
    *,
    session: SessionDep,
    record: CensusRecordUpdate,
    real_ip: Annotated[str | None, Header(alias="X-Real-IP")] = None,
) -> CensusRecord:
    now = datetime.now(tz=timezone.utc)

    await delete_expired_records(session=session, start_time=now)

    if record.deployment_id in settings.DEPLOYMENT_IDS_TO_IGNORE:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Deployment ID is the same as used in example configuration",
        )

    statement = select(CensusRecord).where(
        CensusRecord.deployment_id == record.deployment_id
    )
    results = await session.exec(statement=statement)
    db_record = results.first()

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

            db_record.version = record.version
            db_record.python_version = python_version
            db_record.updated_at = now
            event = CensusRecordEvent.UPDATED
    else:
        db_record = CensusRecord(
            deployment_id=record.deployment_id,
            version=record.version,
            python_version=version_strip_micro(version=record.python_version),
            created_at=now,
            updated_at=now,
        )
        event = CensusRecordEvent.CREATED

    if event:
        db_record.country = (
            await resolve_country_for_ip(ip_address=real_ip) if real_ip else None
        )
        session.add(db_record)
        await session.commit()
        await session.refresh(db_record)

        if send_notification:
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


@router.get("/summary", response_model=CensusSummaries)
async def read_summary(*, session: SessionDep) -> CensusSummaries:
    summaries: dict[str, list[CensusSummary]] = {
        "version": [],
        "python_version": [],
        "country": [],
    }

    for item, values in summaries.items():
        query = f"""
WITH item_counts AS (
    SELECT {item}, COUNT(*) AS item_count FROM censusrecord GROUP BY {item}
),
ranked_items AS (
    SELECT {item}, item_count,
    ROW_NUMBER() OVER (ORDER BY item_count DESC) AS rn FROM item_counts
),
top_items AS (
    SELECT {item}, item_count FROM ranked_items WHERE rn <= 5
    UNION ALL
    SELECT 'other' AS {item},
    SUM(item_count) AS item_count FROM ranked_items WHERE rn > 5
),
total_count AS (
    SELECT SUM(item_count) AS total_count FROM item_counts
)
SELECT ti.{item}, ti.item_count,
ROUND(100.0 * ti.item_count / tc.total_count, 2) AS percentage
FROM top_items ti, total_count tc ORDER BY percentage DESC;
"""
        result = await session.exec(statement=text(query))
        for r in result.fetchall():
            label: str = r[0] or "Unknown"
            count: int = 0 if not r[1] else r[1]
            percentage: float = 0 if not r[2] else r[2]

            if label == "other" and count == 0:
                continue

            values.append(
                CensusSummary(label=label, count=count, percentage=percentage)
            )
        # Sort by count reverse (higher to lower) and consider other always to be last
        values.sort(key=lambda k: k.count if k.label != "other" else 0, reverse=True)

    return CensusSummaries(**summaries)
