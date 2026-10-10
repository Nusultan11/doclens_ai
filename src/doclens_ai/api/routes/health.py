from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(BaseModel):
    status: Literal["alive"]


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    database: Literal["healthy"]


@router.get("/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    return LivenessResponse(status="alive")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "PostgreSQL is unavailable",
            "content": {
                "application/json": {
                    "example": {"status": "not_ready", "database": "unavailable"}
                }
            },
        }
    },
)
async def readiness(request: Request) -> ReadinessResponse | JSONResponse:
    try:
        await request.app.state.database.probe()
    except Exception:  # noqa: BLE001 - health boundary must safely map probe failures to 503.
        logger.warning("Database readiness probe failed")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "database": "unavailable"},
        )

    return ReadinessResponse(status="ready", database="healthy")
