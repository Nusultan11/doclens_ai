from __future__ import annotations

import os

import pytest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://doclens:doclens-local@localhost:5432/doclens_test",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
