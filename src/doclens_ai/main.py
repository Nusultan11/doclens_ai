from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from doclens_ai.api.router import api_router
from doclens_ai.core.config import Settings, get_settings
from doclens_ai.db.session import Database


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    yield
    await application.state.database.dispose()


def create_app(*, settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    application_settings = settings or get_settings()
    application_database = database or Database(application_settings.database_url)

    application = FastAPI(title=application_settings.app_name, lifespan=lifespan)
    application.state.settings = application_settings
    application.state.database = application_database
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
