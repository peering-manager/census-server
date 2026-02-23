import logging
from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlmodel import delete, select, text
from sqlmodel.ext.asyncio.session import AsyncSession

from ..core.config import settings
from ..models import CensusRecord, CensusSummaries, CensusSummary


async def delete_expired_records(*, session: AsyncSession, start_time: datetime) -> int:
    cut_off = start_time - timedelta(days=settings.RECORD_RETENTION)
    result = await session.exec(
        delete(CensusRecord).where(CensusRecord.updated_at < cut_off)
    )
    await session.commit()

    logging.info(f"deleted {result.rowcount} expired census records")
    return result.rowcount


async def get_record_for_update(
    *, session: AsyncSession, deployment_id: str
) -> CensusRecord | None:
    statement = (
        select(CensusRecord)
        .where(CensusRecord.deployment_id == deployment_id)
        .with_for_update()
    )
    results = await session.exec(statement=statement)
    return results.first()


async def create_record(  # noqa: PLR0913
    *,
    session: AsyncSession,
    deployment_id: str,
    version: str,
    python_version: str | None,
    country: str | None,
    now: datetime,
) -> CensusRecord:
    db_record = CensusRecord(
        deployment_id=deployment_id,
        version=version,
        python_version=python_version,
        country=country,
        created_at=now,
        updated_at=now,
    )
    session.add(db_record)
    await session.commit()
    await session.refresh(db_record)
    return db_record


async def update_record(  # noqa: PLR0913
    *,
    session: AsyncSession,
    db_record: CensusRecord,
    version: str,
    python_version: str | None,
    country: str | None,
    now: datetime,
) -> CensusRecord:
    db_record.version = version
    db_record.python_version = python_version
    db_record.country = country
    db_record.updated_at = now
    session.add(db_record)
    await session.commit()
    await session.refresh(db_record)
    return db_record


async def get_records(
    *, session: AsyncSession, offset: int, limit: int
) -> Sequence[CensusRecord]:
    result = await session.exec(select(CensusRecord).offset(offset).limit(limit))
    return result.all()


async def get_summary(*, session: AsyncSession) -> CensusSummaries:
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
