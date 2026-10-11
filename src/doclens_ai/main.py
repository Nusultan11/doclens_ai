from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from doclens_ai.api.router import api_router
from doclens_ai.core.config import Settings, get_settings
from doclens_ai.db.session import Database
from doclens_ai.security import JwtVerifier


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        verifier: JwtVerifier | None = application.state.jwt_verifier
        if verifier is not None:
            await verifier.aclose()
        await application.state.database.dispose()


def create_app(
    *,
    settings: Settings | None = None,
    database: Database | None = None,
    jwt_verifier: JwtVerifier | None = None,
) -> FastAPI:
    application_settings = settings or get_settings()
    application_database = database or Database(application_settings.database_url)

    application = FastAPI(title=application_settings.app_name, lifespan=lifespan)
    application.state.settings = application_settings
    application.state.database = application_database
    application.state.jwt_verifier = jwt_verifier or _build_jwt_verifier(application_settings)
    application.include_router(api_router, prefix="/api/v1")
    return application


def _build_jwt_verifier(settings: Settings) -> JwtVerifier | None:
    if not settings.oidc_is_configured:
        return None
    assert settings.oidc_issuer is not None
    assert settings.oidc_audience is not None
    assert settings.oidc_jwks_url is not None
    try:
        return JwtVerifier(
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience,
            jwks_url=settings.oidc_jwks_url,
            required_scope=settings.oidc_required_scope,
            timeout_seconds=float(settings.oidc_jwks_timeout_seconds),
            cache_ttl_seconds=int(settings.oidc_jwks_cache_ttl_seconds),
        )
    except ValueError:
        return None


app = create_app()
