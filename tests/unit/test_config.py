from __future__ import annotations

import pytest
from pydantic import ValidationError

from doclens_ai.core.config import Settings


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "database_url",
    [
        "not-a-url",
        "sqlite+aiosqlite:///local.db",
        "postgresql://doclens:local@localhost/doclens",
        "postgresql+asyncpg://doclens:local@localhost",
    ],
)
def test_database_url_requires_async_postgresql(database_url: str) -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(database_url=database_url, _env_file=None)


def test_settings_accept_async_postgresql_url() -> None:
    database_url = "postgresql+asyncpg://doclens:local@localhost/doclens"

    settings = Settings(database_url=database_url, _env_file=None)

    assert settings.database_url == database_url
    assert settings.environment == "local"
