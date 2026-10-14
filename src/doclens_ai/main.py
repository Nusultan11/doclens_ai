from __future__ import annotations

import logging
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
        from doclens_ai.core.search_config import SearchSettings

        settings = SearchSettings()
        if settings.enabled:
            from doclens_ai.search_runtime import build_search_runtime

            application.state.retrieval_service = await build_search_runtime(
                application.state.database.session_factory, settings
            )
    except Exception:
        # No exception details: model paths/credentials and document-derived values are private.
        logging.getLogger(__name__).warning("search_runtime_unavailable")
    try:
        from doclens_ai.core.rag_config import RagSettings

        rag_settings = RagSettings()
        if rag_settings.enabled:
            from doclens_ai.rag_runtime import build_rag_runtime

            application.state.rag_service = build_rag_runtime(
                application.state.retrieval_service, rag_settings
            )
    except Exception:
        logging.getLogger(__name__).warning("rag_runtime_unavailable")
    try:
        yield
    finally:
        rag = application.state.rag_service
        if rag is not None:
            await rag.aclose()
        service = application.state.retrieval_service
        if service is not None:
            await service.aclose()
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
    application.state.retrieval_service = None
    application.state.rag_service = None
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
