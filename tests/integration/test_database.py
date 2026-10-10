from __future__ import annotations

import asyncio
import os

import pytest

from doclens_ai.core.config import Settings
from doclens_ai.db.session import Database


@pytest.mark.integration
def test_real_postgresql_probe() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    settings = Settings(database_url=database_url, _env_file=None)

    async def probe_and_dispose() -> None:
        database = Database(settings.database_url)
        try:
            await database.probe()
        finally:
            await database.dispose()

    asyncio.run(probe_and_dispose())
