from datetime import datetime, timezone

import pytest
from httpx import AsyncClient, codes
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from census_api.core.config import settings
from census_api.models import CensusRecord


@pytest.mark.usefixtures("discord_notification")
async def test_create_census_record(client: AsyncClient) -> None:
    response = await client.post(
        f"{settings.API_V1_STR}/records/",
        json={
            "deployment_id": "aaaaaaaaa",
            "version": "1.9.0",
            "python_version": "3.12.0",
        },
    )
    data = response.json()

    assert response.status_code == codes.OK
    assert data["deployment_id"] == "aaaaaaaaa"
    assert data["version"] == "1.9.0"
    assert data["python_version"] == "3.12.0"
    assert data["created_at"]
    assert data["updated_at"]


@pytest.mark.usefixtures("discord_notification")
async def test_update_census_record(session: AsyncSession, client: AsyncClient) -> None:
    now = datetime.now(tz=timezone.utc)
    census = CensusRecord(
        deployment_id="aaaaaaaaa",
        version="1.8.0",
        python_version="3.10.0",
        country="FR",
        created_at=now,
        updated_at=now,
    )
    session.add(census)
    await session.commit()

    response = await client.post(
        f"{settings.API_V1_STR}/records/",
        json={
            "deployment_id": "aaaaaaaaa",
            "version": "1.9.0",
            "python_version": "3.12.0",
        },
    )
    data = response.json()

    assert response.status_code == codes.OK

    results = await session.exec(
        statement=select(CensusRecord).where(
            CensusRecord.deployment_id == data["deployment_id"]
        )
    )
    records = results.all()

    assert len(records) == 1
    assert records[0].deployment_id == data["deployment_id"]
    assert records[0].version == data["version"]
    assert records[0].python_version == data["python_version"]
    assert records[0].created_at == datetime.fromisoformat(data["created_at"])
    assert records[0].updated_at == datetime.fromisoformat(data["updated_at"])


async def test_read_censuses(session: AsyncSession, client: AsyncClient) -> None:
    now = datetime.now(tz=timezone.utc)
    census_1 = CensusRecord(
        deployment_id="aaaaaaaaa",
        version="1.8.0",
        python_version="3.10.0",
        country="FR",
        created_at=now,
        updated_at=now,
    )
    census_2 = CensusRecord(
        deployment_id="bbbbbbbbb",
        version="1.9.0",
        python_version="3.12.0",
        country="GB",
        created_at=now,
        updated_at=now,
    )
    session.add(census_1)
    session.add(census_2)
    await session.commit()

    response = await client.get(f"{settings.API_V1_STR}/records/")
    data = response.json()

    assert response.status_code == codes.OK

    assert len(data) == 2  # noqa: PLR2004
    assert data[0]["deployment_id"] == census_1.deployment_id
    assert data[0]["version"] == census_1.version
    assert data[0]["python_version"] == census_1.python_version
    assert data[0]["country"] == census_1.country
    assert datetime.fromisoformat(data[0]["created_at"]) == census_1.created_at
    assert datetime.fromisoformat(data[0]["updated_at"]) == census_1.updated_at
    assert data[1]["deployment_id"] == census_2.deployment_id
    assert data[1]["version"] == census_2.version
    assert data[1]["python_version"] == census_2.python_version
    assert data[1]["country"] == census_2.country
    assert datetime.fromisoformat(data[1]["created_at"]) == census_1.created_at
    assert datetime.fromisoformat(data[1]["updated_at"]) == census_1.updated_at
