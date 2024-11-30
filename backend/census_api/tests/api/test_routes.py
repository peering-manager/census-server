from datetime import datetime, timedelta, timezone

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
    assert data["python_version"] == "3.12"
    assert data["created_at"]
    assert data["updated_at"]


async def test_create_census_record_fail(client: AsyncClient) -> None:
    settings.DEPLOYMENT_IDS_TO_IGNORE = ["invalid"]

    response = await client.post(
        f"{settings.API_V1_STR}/records/",
        json={
            "deployment_id": "invalid",
            "version": "1.9.0",
            "python_version": "3.12.0",
        },
    )
    assert response.status_code == codes.NOT_ACCEPTABLE


@pytest.mark.usefixtures("discord_notification")
async def test_update_census_record(session: AsyncSession, client: AsyncClient) -> None:
    # Insert who a date to avoid rate limiting
    past = datetime.now(tz=timezone.utc) - timedelta(seconds=settings.RATE_LIMIT)
    census = CensusRecord(
        deployment_id="aaaaaaaaa",
        version="1.8.0",
        python_version="3.10",
        country="FR",
        created_at=past,
        updated_at=past,
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


@pytest.mark.usefixtures("discord_notification")
async def test_delete_expired_census_record(
    session: AsyncSession, client: AsyncClient
) -> None:
    # Create an expired record
    past = datetime.now(tz=timezone.utc) - timedelta(days=settings.RECORD_RETENTION)
    census = CensusRecord(
        deployment_id="aaaaaaaaa",
        version="1.8.0",
        python_version="3.10.0",
        country="FR",
        created_at=past,
        updated_at=past,
    )
    session.add(census)
    await session.commit()

    # Make a request to force records cleanup
    await client.post(
        f"{settings.API_V1_STR}/records/",
        json={
            "deployment_id": "bbbbbbbbb",
            "version": "1.9.0",
            "python_version": "3.12.0",
        },
    )

    results = await session.exec(statement=select(CensusRecord))
    records = results.all()

    # First record should have been deleted
    assert len(records) == 1
    assert records[0].created_at.astimezone(timezone.utc) > past
    assert records[0].updated_at.astimezone(timezone.utc) > past


async def test_update_census_record_rate_limited(
    session: AsyncSession, client: AsyncClient
) -> None:
    past = datetime.now(tz=timezone.utc) - timedelta(seconds=10)
    census = CensusRecord(
        deployment_id="aaaaaaaaa",
        version="1.8.0",
        python_version="3.10",
        country="FR",
        created_at=past,
        updated_at=past,
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

    # Rate limit should have been hit, therefore the record should not have been updated
    assert len(records) == 1
    assert records[0].deployment_id == data["deployment_id"]
    assert records[0].version == data["version"]
    assert records[0].python_version == data["python_version"]
    assert records[0].created_at == past
    assert records[0].updated_at == past


async def test_read_censuses(session: AsyncSession, client: AsyncClient) -> None:
    now = datetime.now(tz=timezone.utc)
    census_1 = CensusRecord(
        deployment_id="aaaaaaaaa",
        version="1.8.0",
        python_version="3.10",
        country="FR",
        created_at=now,
        updated_at=now,
    )
    census_2 = CensusRecord(
        deployment_id="bbbbbbbbb",
        version="1.9.0",
        python_version="3.12",
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


async def test_read_summary(session: AsyncSession, client: AsyncClient) -> None:
    now = datetime.now(tz=timezone.utc)
    deployment_ids = [
        "a" * 10,
        "b" * 10,
        "c" * 10,
        "d" * 10,
        "e" * 10,
        "f" * 10,
        "0" * 10,
        "1" * 10,
        "2" * 10,
        "3" * 10,
    ]
    versions = [
        "1.8.0",
        "1.8.0",
        "1.9.0",
        "1.9.0",
        "1.9.0",
        "1.9.0",
        "1.7.0",
        "1.7.0",
        "1.6.0",
        "1.5.0",
    ]
    python_versions = [
        "3.10",
        "3.11",
        "3.11",
        "3.12",
        "3.12",
        "3.12",
        "3.9",
        "3.9",
        "3.9",
        "3.9",
    ]
    countries = ["FR", "GB", "DE", "IT", "FR", "GB", "US", "US", "US", "CA"]
    for deployment_id, version, python_version, country in zip(
        deployment_ids, versions, python_versions, countries, strict=False
    ):
        session.add(
            CensusRecord(
                deployment_id=deployment_id,
                version=version,
                python_version=python_version,
                country=country,
                created_at=now,
                updated_at=now,
            )
        )
    await session.commit()

    response = await client.get(f"{settings.API_V1_STR}/records/summary")
    data = response.json()

    assert response.status_code == codes.OK
    assert data == {
        "country": [
            {
                "count": 3,
                "label": "US",
                "percentage": 30.0,
            },
            {
                "count": 2,
                "label": "FR",
                "percentage": 20.0,
            },
            {
                "count": 2,
                "label": "GB",
                "percentage": 20.0,
            },
            {
                "count": 1,
                "label": "CA",
                "percentage": 10.0,
            },
            {
                "count": 1,
                "label": "DE",
                "percentage": 10.0,
            },
            {
                "count": 1,
                "label": "other",
                "percentage": 10.0,
            },
        ],
        "python_version": [
            {
                "count": 4,
                "label": "3.9",
                "percentage": 40.0,
            },
            {
                "count": 3,
                "label": "3.12",
                "percentage": 30.0,
            },
            {
                "count": 2,
                "label": "3.11",
                "percentage": 20.0,
            },
            {
                "count": 1,
                "label": "3.10",
                "percentage": 10.0,
            },
        ],
        "version": [
            {
                "count": 4,
                "label": "1.9.0",
                "percentage": 40.0,
            },
            {
                "count": 2,
                "label": "1.7.0",
                "percentage": 20.0,
            },
            {
                "count": 2,
                "label": "1.8.0",
                "percentage": 20.0,
            },
            {
                "count": 1,
                "label": "1.5.0",
                "percentage": 10.0,
            },
            {
                "count": 1,
                "label": "1.6.0",
                "percentage": 10.0,
            },
        ],
    }
