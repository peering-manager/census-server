from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from sqlmodel import select

from census_api.backend_pre_start import init


@pytest.mark.asyncio
async def test_init_successful_connection():
    engine_mock = MagicMock()

    session_mock = AsyncMock()
    session_mock.exec.return_value = True
    session_mock.__aenter__.return_value = session_mock
    session_mock.__aexit__.return_value = None

    sessionmaker_mock = MagicMock(return_value=lambda: session_mock)

    with patch("census_api.backend_pre_start.sessionmaker", sessionmaker_mock):
        try:
            await init(engine=engine_mock)
            connection_successful = True
        except Exception:
            connection_successful = False

        assert (
            connection_successful
        ), "The database connection should be successful and not raise an exception."
        session_mock.exec.assert_called_once_with(ANY)
        assert str(session_mock.exec.call_args[0][0]) == str(
            select(1)
        ), "The session should execute a select statement once."
