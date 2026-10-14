"""Opt-in local generation shares the existing authorized retrieval runtime."""

from doclens_ai.core.rag_config import RagSettings
from doclens_ai.llm.provider import GeneratorUnavailable, LocalGenerator
from doclens_ai.services.rag import RagService


def build_rag_runtime(retrieval, settings: RagSettings):
    if retrieval is None or not settings.enabled:
        raise GeneratorUnavailable()
    return RagService(retrieval, LocalGenerator(settings), settings)
