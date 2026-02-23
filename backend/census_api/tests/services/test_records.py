from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from census_api.core.config import settings
from census_api.models import CensusRecord, CensusRecordUpdate
from census_api.services.records import process_census_report


def _utcnow() -> datetime:
    """Return a naive UTC datetime matching what SQLite round-trips."""
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)


@pytest.fixture
def mock_notifier() -> Generator[AsyncMock]:
    mock = AsyncMock()
    with patch("census_api.services.records.get_notifiers", return_value=[mock]):
        yield mock


@pytest.fixture
def mock_country() -> Generator[None]:
    with patch(
        "census_api.services.records.resolve_country_for_ip",
        new_callable=AsyncMock,
        return_value="FR",
    ):
        yield


@pytest.mark.usefixtures("mock_notifier", "mock_country")
async def test_process_census_report_new_record(session: AsyncSession) -> None:
    record = CensusRecordUpdate(
        deployment_id="new-deploy", version="1.9.0", python_version="3.12.0"
    )
    result = await process_census_report(
        session=session, record=record, real_ip="1.2.3.4"
    )
    assert result.deployment_id == "new-deploy"
    assert result.version == "1.9.0"
    assert result.python_version == "3.12"
    assert result.country == "FR"


@pytest.mark.usefixtures("mock_notifier", "mock_country")
async def test_process_census_report_update_record(session: AsyncSession) -> None:
    past = _utcnow() - timedelta(seconds=settings.RATE_LIMIT + 1)
    session.add(
        CensusRecord(
            deployment_id="existing",
            version="1.8.0",
            python_version="3.11",
            country="DE",
            created_at=past,
            updated_at=past,
        )
    )
    await session.commit()

    record = CensusRecordUpdate(
        deployment_id="existing", version="1.9.0", python_version="3.12.0"
    )
    result = await process_census_report(
        session=session, record=record, real_ip="1.2.3.4"
    )
    assert result.version == "1.9.0"
    assert result.python_version == "3.12"
    assert result.updated_at > past


@pytest.mark.usefixtures("mock_notifier", "mock_country")
async def test_process_census_report_rate_limited(session: AsyncSession) -> None:
    recent = _utcnow() - timedelta(seconds=10)
    session.add(
        CensusRecord(
            deployment_id="rate-limited",
            version="1.8.0",
            python_version="3.11",
            country="DE",
            created_at=recent,
            updated_at=recent,
        )
    )
    await session.commit()

    record = CensusRecordUpdate(
        deployment_id="rate-limited", version="1.9.0", python_version="3.12.0"
    )
    result = await process_census_report(
        session=session, record=record, real_ip="1.2.3.4"
    )
    # Record should not have been updated
    assert result.version == "1.8.0"
    assert result.updated_at == recent


@pytest.mark.usefixtures("mock_notifier", "mock_country")
async def test_process_census_report_ignored_deployment_id(
    session: AsyncSession,
) -> None:
    settings.DEPLOYMENT_IDS_TO_IGNORE = ["ignored-id"]

    record = CensusRecordUpdate(
        deployment_id="ignored-id", version="1.9.0", python_version="3.12.0"
    )
    with pytest.raises(HTTPException) as exc_info:
        await process_census_report(session=session, record=record, real_ip=None)
    assert exc_info.value.status_code == status.HTTP_406_NOT_ACCEPTABLE


@pytest.mark.usefixtures("mock_country")
async def test_process_census_report_no_notification_when_unchanged(
    session: AsyncSession,
    mock_notifier: AsyncMock,
) -> None:
    past = _utcnow() - timedelta(seconds=settings.RATE_LIMIT + 1)
    session.add(
        CensusRecord(
            deployment_id="unchanged",
            version="1.9.0",
            python_version="3.12",
            country="FR",
            created_at=past,
            updated_at=past,
        )
    )
    await session.commit()

    # Same version and python_version — no notification expected
    record = CensusRecordUpdate(
        deployment_id="unchanged", version="1.9.0", python_version="3.12.0"
    )
    await process_census_report(session=session, record=record, real_ip="1.2.3.4")
    mock_notifier.send.assert_not_called()
