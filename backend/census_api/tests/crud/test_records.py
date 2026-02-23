from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from census_api.core.config import settings
from census_api.crud.records import (
    create_record,
    delete_expired_records,
    get_record_for_update,
    get_records,
    get_summary,
    update_record,
)
from census_api.models import CensusRecord


def _utcnow() -> datetime:
    """Return a naive UTC datetime matching what SQLite round-trips."""
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)


@pytest.fixture
async def sample_record(session: AsyncSession) -> CensusRecord:
    now = _utcnow()
    record = CensusRecord(
        deployment_id="test-deploy",
        version="1.9.0",
        python_version="3.12",
        country="FR",
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    await session.commit()
    return record


async def test_delete_expired_records(session: AsyncSession) -> None:
    past = _utcnow() - timedelta(days=settings.RECORD_RETENTION + 1)
    session.add(
        CensusRecord(
            deployment_id="expired",
            version="1.0.0",
            python_version="3.10",
            country=None,
            created_at=past,
            updated_at=past,
        )
    )
    await session.commit()

    now = _utcnow()
    count = await delete_expired_records(session=session, start_time=now)
    assert count == 1


async def test_delete_expired_records_keeps_fresh(session: AsyncSession) -> None:
    now = _utcnow()
    session.add(
        CensusRecord(
            deployment_id="fresh",
            version="1.0.0",
            python_version="3.12",
            country=None,
            created_at=now,
            updated_at=now,
        )
    )
    await session.commit()

    count = await delete_expired_records(session=session, start_time=now)
    assert count == 0


async def test_get_record_for_update_exists(
    session: AsyncSession, sample_record: CensusRecord
) -> None:
    result = await get_record_for_update(
        session=session, deployment_id=sample_record.deployment_id
    )
    assert result is not None
    assert result.deployment_id == sample_record.deployment_id


async def test_get_record_for_update_missing(session: AsyncSession) -> None:
    result = await get_record_for_update(session=session, deployment_id="nonexistent")
    assert result is None


async def test_create_record(session: AsyncSession) -> None:
    now = _utcnow()
    record = await create_record(
        session=session,
        deployment_id="new-deploy",
        version="2.0.0",
        python_version="3.12",
        country="DE",
        now=now,
    )
    assert record.deployment_id == "new-deploy"
    assert record.version == "2.0.0"
    assert record.python_version == "3.12"
    assert record.country == "DE"
    assert record.created_at == now
    assert record.updated_at == now


async def test_update_record(
    session: AsyncSession, sample_record: CensusRecord
) -> None:
    now = _utcnow()
    updated = await update_record(
        session=session,
        db_record=sample_record,
        version="2.0.0",
        python_version="3.13",
        country="GB",
        now=now,
    )
    assert updated.deployment_id == sample_record.deployment_id
    assert updated.version == "2.0.0"
    assert updated.python_version == "3.13"
    assert updated.country == "GB"
    assert updated.updated_at == now


async def test_get_records(session: AsyncSession, sample_record: CensusRecord) -> None:
    records = await get_records(session=session, offset=0, limit=100)
    assert len(records) == 1
    assert records[0].deployment_id == sample_record.deployment_id


async def test_get_summary(session: AsyncSession) -> None:
    now = _utcnow()
    for i in range(3):
        session.add(
            CensusRecord(
                deployment_id=f"deploy-{i}",
                version="1.9.0",
                python_version="3.12",
                country="FR",
                created_at=now,
                updated_at=now,
            )
        )
    await session.commit()

    summaries = await get_summary(session=session)
    assert len(summaries.version) >= 1
    assert summaries.version[0].label == "1.9.0"
    assert summaries.version[0].count == 3  # noqa: PLR2004
