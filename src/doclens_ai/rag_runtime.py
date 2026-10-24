"""Opt-in local generation shares the existing authorized retrieval runtime."""

from doclens_ai.core.rag_config import RagSettings
from doclens_ai.llm.provider import GeneratorUnavailable, LocalGenerator
from doclens_ai.services.rag import RagService, TokenCounter


def build_rag_runtime(
    retrieval, settings: RagSettings, *, token_counter: TokenCounter | None = None
):
    if retrieval is None or not settings.enabled:
        raise GeneratorUnavailable()
    return RagService(retrieval, LocalGenerator(settings), settings, token_counter=token_counter)
