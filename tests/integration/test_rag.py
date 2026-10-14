from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import delete

from doclens_ai.core.rag_config import RagSettings
from doclens_ai.models import CanonicalChunk, WorkspaceMembership
from doclens_ai.services.rag import AnswerInput, RagService
from doclens_ai.services.retrieval import SearchForbidden
from tests.integration.test_retrieval import (
    _claim,
    _complete,
    _extraction_worker,
    _index,
    _next_version_or_run,
    _retrieval_context,
)

pytestmark = [pytest.mark.integration, pytest.mark.storage]


class EvidenceGenerator:
    """Deterministic test double, NOT a real model or a quality evaluation."""

    def __init__(self, *, before_return=None, mutation=None):
        self.before_return, self.mutation, self.calls = before_return, mutation, 0
        self.messages = None

    async def generate(self, messages):
        self.calls += 1
        self.messages = messages
        data = json.loads(messages[1]["content"])
        if self.before_return:
            await self.before_return(data)
        if self.mutation == "malformed":
            return "private broken model output"
        if self.mutation == "refuse":
            return json.dumps(
                {
                    "answerable": False,
                    "answer": None,
                    "citations": [],
                    "reason": "insufficient_evidence",
                }
            )
        item = data["evidence"][0]
        # An extractive fixture answer lets the test inspect exact supporting spans.
        text = item["text"]
        reference = {
            "chunk_id": item["chunk_id"],
            "document_version_id": item["document_version_id"],
            "quote": text,
            "quote_start": 0,
            "quote_end": len(text),
            "answer_start": 0,
            "answer_end": len(text),
        }
        if self.mutation == "forged":
            reference["chunk_id"] = str(uuid4())
        elif self.mutation == "version":
            reference["document_version_id"] = str(uuid4())
        elif self.mutation == "quote":
            reference["quote"] = "unrelated private quote"
        elif self.mutation == "metadata":
            reference["source_locator"] = {"page_number": 1000}
        return json.dumps(
            {"answerable": True, "answer": text, "reason": None, "citations": [reference]}
        )

    async def aclose(self):
        pass


@pytest.mark.anyio
@pytest.mark.parametrize(
    "mutation", [None, "refuse", "malformed", "forged", "version", "quote", "metadata"]
)
async def test_real_retrieval_grounding_and_invalid_output_isolation(
    migrated_database_url, test_storage_settings, mutation
):
    async with _retrieval_context(migrated_database_url, test_storage_settings) as ctx:
        _, retrieval, user, _, _, _, revisions = ctx
        generator = EvidenceGenerator(mutation=mutation)
        service = RagService(retrieval, generator, RagSettings(_env_file=None))
        request = AnswerInput(workspace_id=revisions[0].workspace_id, question="Fixture question?")
        result = await service.answer(user_id=user.id, request=request)
        assert result.response.answerable == (mutation is None)
        if mutation is None:
            reference = result.response.citations[0]
            assert reference.document_id == revisions[0].document_id
            assert reference.document_version_id == str(revisions[0].document_version_id)
            assert reference.source_locator.document_format == "docx"
        else:
            assert result.response.answer is None and result.response.citations == []
            assert result.response.reason == "insufficient_evidence"
        assert all(
            item["document_id"] == str(revisions[0].document_id)
            for item in json.loads(generator.messages[1]["content"])["evidence"]
        )
        with pytest.raises(SearchForbidden):
            await service.answer(
                user_id=user.id,
                request=AnswerInput(
                    workspace_id=revisions[1].workspace_id, question="Foreign question?"
                ),
            )
        assert generator.calls == 1
        # A client document selector cannot authorize a foreign source.
        empty = await service.answer(
            user_id=user.id,
            request=AnswerInput(
                workspace_id=revisions[0].workspace_id,
                question="Foreign document?",
                document_ids=[revisions[1].document_id],
            ),
        )
        assert empty.response.reason == "no_relevant_context" and generator.calls == 1


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", ["revoked", "cutover", "deleted", "revoked_refusal"])
async def test_generation_time_pg_changes_invalidate_whole_answer(
    migrated_database_url, test_storage_settings, mutation
):
    async with _retrieval_context(migrated_database_url, test_storage_settings) as ctx:
        env, retrieval, user, _, first, _, revisions = ctx
        factory, storage, _, worker, _, _ = env
        if mutation == "cutover":
            await _next_version_or_run(factory, first, reprocess=False)
            assert await _extraction_worker(factory, storage).run_once()
            claim = await _claim(worker)
            verified = await _index(worker, claim)

        async def change(data):
            if mutation == "cutover":
                await _complete(worker, claim, verified)
            else:
                async with factory() as session, session.begin():
                    if mutation.startswith("revoked"):
                        await session.execute(
                            delete(WorkspaceMembership).where(
                                WorkspaceMembership.user_id == user.id
                            )
                        )
                    else:
                        # Delete UNcited evidence too: no partially supported answer is released.
                        await session.execute(
                            delete(CanonicalChunk).where(
                                CanonicalChunk.id == data["evidence"][-1]["chunk_id"]
                            )
                        )

        generator = EvidenceGenerator(
            before_return=change, mutation="refuse" if mutation == "revoked_refusal" else None
        )
        service = RagService(retrieval, generator, RagSettings(_env_file=None))
        request = AnswerInput(workspace_id=revisions[0].workspace_id, question="Fixture question?")
        if mutation.startswith("revoked"):
            with pytest.raises(SearchForbidden):
                await service.answer(user_id=user.id, request=request)
        else:
            result = await service.answer(user_id=user.id, request=request)
            assert result.response.reason == "source_unavailable"
            assert result.response.answer is None and result.response.citations == []


@pytest.mark.anyio
async def test_revalidation_is_exact_and_does_not_query_qdrant(
    migrated_database_url, test_storage_settings, monkeypatch
):
    async with _retrieval_context(migrated_database_url, test_storage_settings) as ctx:
        _, retrieval, user, _, _, _, revisions = ctx
        workspace = revisions[0].workspace_id
        outcome = await retrieval.search(
            user_id=user.id,
            request=AnswerInput(workspace_id=workspace, question="Fixture?").search_input(),
        )

        async def network_forbidden(*args, **kwargs):
            raise AssertionError("post-generation authorization must be PG only")

        monkeypatch.setattr(retrieval.vector, "search", network_forbidden)
        assert await retrieval.revalidate(
            user_id=user.id, workspace_id=workspace, evidence=outcome.results
        )
        item = outcome.results[0]
        for changed in (
            replace(item, workspace_id=uuid4()),
            replace(item, text="wrong"),
            replace(item, document_id=uuid4()),
            replace(item, document_version_id=uuid4()),
            replace(item, index_revision_id=uuid4()),
            replace(item, source_sha256="b" * 64),
        ):
            assert not await retrieval.revalidate(
                user_id=user.id, workspace_id=workspace, evidence=(changed,)
            )
        assert not await retrieval.revalidate(
            user_id=user.id, workspace_id=workspace, evidence=(item, item)
        )
        results = await asyncio.gather(
            *(
                retrieval.revalidate(
                    user_id=user.id, workspace_id=workspace, evidence=outcome.results
                )
                for _ in range(4)
            )
        )
        assert all(results)
