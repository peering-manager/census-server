from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from pytest_httpx import HTTPXMock
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.pool import StaticPool

from census_api.core.config import settings
from census_api.core.dependencies import get_session
from census_api.main import app


@pytest.fixture(name="session")
async def session_fixture() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def init_models() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)

    await init_models()

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture(name="client")
async def client_fixture(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def get_session_override() -> AsyncSession:
        return session

    app.dependency_overrides[get_session] = get_session_override

    async with AsyncClient(
        base_url="http://test.example.com", transport=ASGITransport(app=app)
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(name="discord_notification")
async def _discord_notification_fixture(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=settings.DISCORD_WEBHOOK_URL)
