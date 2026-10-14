from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from doclens_ai.api.dependencies import get_current_user, get_rag_service
from doclens_ai.llm.provider import GeneratorUnavailable
from doclens_ai.models import User
from doclens_ai.services.rag import AnswerInput, AnswerResponse, RagService
from doclens_ai.services.retrieval import SearchForbidden, SearchUnavailable


class SanitizedAnswerRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request):
            try:
                return await original(request)
            except RequestValidationError:
                # FastAPI's default validation response echoes private user inputs.
                raise HTTPException(status_code=422, detail="invalid answer request") from None

        return handler


router = APIRouter(tags=["answers"], route_class=SanitizedAnswerRoute)


@router.post("/answers", response_model=AnswerResponse)
async def answer_question(
    request: AnswerInput,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[RagService, Depends(get_rag_service)],
) -> AnswerResponse:
    try:
        return (await service.answer(user_id=user.id, request=request)).response
    except SearchForbidden:
        raise HTTPException(status_code=403, detail="workspace access denied") from None
    except (SearchUnavailable, GeneratorUnavailable):
        raise HTTPException(status_code=503, detail="answer service is unavailable") from None
