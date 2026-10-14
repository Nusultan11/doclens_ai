from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from doclens_ai.api.dependencies import get_current_user, get_retrieval_service
from doclens_ai.models import User
from doclens_ai.services.retrieval import (
    RetrievalService,
    SearchForbidden,
    SearchInput,
    SearchUnavailable,
    SourceLocator,
)

router = APIRouter(tags=["search"])


class SearchHitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: UUID
    document_id: UUID
    document_version_id: UUID
    score: float = Field(allow_inf_nan=False)
    text: str
    source_locator: SourceLocator


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    results: list[SearchHitResponse]


@router.post("/search", response_model=SearchResponse, response_model_exclude_none=True)
async def search_documents(
    request: SearchInput,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> SearchResponse:
    try:
        outcome = await service.search(user_id=user.id, request=request)
    except SearchForbidden:
        raise HTTPException(status_code=403, detail="workspace access denied") from None
    except SearchUnavailable:
        raise HTTPException(status_code=503, detail="search service is unavailable") from None
    return SearchResponse(
        results=[
            SearchHitResponse(
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                document_version_id=hit.document_version_id,
                score=hit.score,
                text=hit.text,
                source_locator=hit.locator,
            )
            for hit in outcome.results
        ]
    )
