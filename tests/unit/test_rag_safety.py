"""Synthetic safety regressions, not independent model/semantic qualification."""

from dataclasses import replace
from uuid import uuid4

import pytest

from doclens_ai.chunking.ir import chunk_verified_ir
from doclens_ai.llm.provider import GeneratorUnavailable
from doclens_ai.rag_eval import SyntheticRetrieval
from doclens_ai.services.rag import AnswerInput, RagService, pack_context
from tests.unit.test_ir_evidence import linked_table, policy, review, source
from tests.unit.test_rag import FakeGenerator, answer_data, settings


async def hit(text=None):
    request = AnswerInput(workspace_id=uuid4(), question="Synthetic count?")
    item = (
        await SyntheticRetrieval().search(user_id=uuid4(), request=request.search_input())
    ).results[0]
    return item if text is None else replace(item, text=text)


@pytest.mark.anyio
async def test_complete_atomic_chunk_is_excluded_instead_of_losing_its_facts():
    ir = linked_table()
    header = ir.elements[0].model_copy(update={"text": "Net amount " + "context " * 540})
    ir = ir.model_copy(update={"elements": (header, *ir.elements[1:])})
    outcome = chunk_verified_ir(
        ir,
        expected=source(),
        review=review(ir),
        policy=policy(ir, allow_verified_pdf=True),
        max_characters=6000,
    )
    assert outcome.status == "complete" and len(outcome.chunks) == 1
    item = await hit(outcome.chunks[0].text)
    assert all(value in item.text for value in ("-001.50", "kg", "A1*-1", "2026"))
    context = pack_context("Net amount?", (item,), settings())
    assert context.evidence == () and context.texts == ()
    assert context.excluded[0].reason == "chunk_limit"
    complete = pack_context("Net amount?", (item,), settings(max_chunk_chars=6000))
    assert complete.texts == (item.text,) and not complete.excluded


@pytest.mark.anyio
@pytest.mark.parametrize(
    "evidence,answer,supported",
    [
        ("Synthetic count: 7", "999 kg", False),
        ("Synthetic count: 7", "7", True),
        ("Net mass: -001.50 kg for 2026.", "-001.50 kg for 2026", True),
        ("Net mass: -001.50 kg for 2026.", "+001.50 kg for 2026", False),
        ("Net mass: -001.50 kg for 2026.", "001.50 kg for 2026", False),
        ("Net mass: -001.50 kg for 2026.", "-001.50 mg for 2026", False),
        ("Net mass: -001.50 kg for 2026.", "-001.50 kg for 2025", False),
        ("Net mass: -001.50 kg for 2026.", "-001.50", False),
        ("Period: 2026\nNet mass: -001.50 kg", "-001.50 kg", False),
        ("Net mass: -001.50 kg for 2026.", "50 kg", False),
        ("Масса: −001,50 кг за 2026 год.", "−001,50 кг за 2026 год", True),
        ("Масса: −001,50 кг за 2026 год.", "−001.50 кг за 2026 год", False),
        ("Mass (kg): 7", "7", False),
        ("Mass kg: 7", "7", False),
        ("Not allowed: 7 kg", "7 kg", False),
        ("Value: 0007.00%", "7%", False),
        ("Value: 0007.00%", "0007.00%", True),
        ("Value: 1e-7 kg for 2026", "1e7 kg for 2026", False),
        ("Count: ７", "7", False),
        ("No numerical value is specified.", "nine kg", False),
        ("Synthetic count: 7", "nine kg", False),
        ("Synthetic name: ALPHA", "ALPHA", True),
    ],
)
async def test_numeric_claim_requires_source_fact_not_just_a_real_citation(
    evidence, answer, supported
):
    item = await hit(evidence)

    class Retrieval(SyntheticRetrieval):
        async def search(self, **kwargs):
            result = await super().search(**kwargs)
            return replace(result, results=(item,))

    async def generate(messages):
        import json

        return json.dumps(answer_data(item, answer))

    result = await RagService(Retrieval(), FakeGenerator(generate), settings()).answer(
        user_id=uuid4(), request=AnswerInput(workspace_id=item.workspace_id, question="Value?")
    )
    assert result.response.answerable is supported
    assert result.invalid_output is (not supported)
    if supported:
        assert result.response.answer == answer
    else:
        assert result.response.reason == "insufficient_evidence"
        assert result.response.answer is None and result.response.citations == []


@pytest.mark.anyio
async def test_character_budget_skip_then_fit_preserves_whole_later_chunk():
    small = await hit("Value: -001.50 kg in 2026")
    large = replace(small, chunk_id=uuid4(), score=2, text="x" * 3900)
    config = settings(max_context_chars=4000)
    context = pack_context("Question?", [large, small], config)
    assert context.texts == (small.text,)
    assert context.excluded[0].chunk_id == large.chunk_id
    assert context.excluded[0].reason == "context_limit"
    assert len(context.messages[1]["content"]) <= config.max_context_chars


@pytest.mark.anyio
async def test_token_budget_counts_full_messages_and_reserves_output():
    item = await hit("Value: -001.50 kg in 2026")
    config = settings(context_window_tokens=128, max_output_tokens=64)
    observed = []

    def counter(messages):
        observed.append(messages)
        return 64

    exact = pack_context("Question?", [item], config, token_counter=counter)
    assert exact.texts == (item.text,) and observed == [exact.messages]
    assert observed[0][0]["role"] == "system"
    excluded = pack_context("Question?", [item], config, token_counter=lambda _: 65)
    assert excluded.evidence == () and excluded.excluded[0].reason == "token_limit"
    for invalid in (None, lambda _: -1, lambda _: True, lambda _: 1.5):
        with pytest.raises(GeneratorUnavailable):
            pack_context("Question?", [item], config, token_counter=invalid)


@pytest.mark.anyio
async def test_budget_exclusion_refuses_without_inference_and_rechecks_acl():
    item = await hit("-001.50 kg " * 500)

    class Retrieval(SyntheticRetrieval):
        checked = False

        async def search(self, **kwargs):
            return replace(await super().search(**kwargs), results=(item,))

        async def revalidate(self, **kwargs):
            self.checked = True
            assert kwargs["evidence"] == ()
            return True

    retrieval, generator = Retrieval(), FakeGenerator()
    result = await RagService(retrieval, generator, settings()).answer(
        user_id=uuid4(), request=AnswerInput(workspace_id=item.workspace_id, question="Value?")
    )
    assert result.response.reason == "insufficient_evidence"
    assert not result.invalid_output and result.context_count == 0 and result.retrieved_count == 1
    assert retrieval.checked and generator.calls == 0


@pytest.mark.anyio
async def test_cropped_quote_cannot_hide_sign_unit_or_period():
    import json

    item = await hit("Net mass: -001.50 kg for 2026.")

    class Retrieval(SyntheticRetrieval):
        async def search(self, **kwargs):
            return replace(await super().search(**kwargs), results=(item,))

    async def generate(messages):
        data = answer_data(item, "001.50")
        start = item.text.index("001.50")
        data["citations"][0].update(quote="001.50", quote_start=start, quote_end=start + 6)
        return json.dumps(data)

    result = await RagService(Retrieval(), FakeGenerator(generate), settings()).answer(
        user_id=uuid4(), request=AnswerInput(workspace_id=item.workspace_id, question="Value?")
    )
    assert result.invalid_output and result.response.reason == "insufficient_evidence"


@pytest.mark.anyio
async def test_runtime_forwards_trusted_token_counter_and_missing_counter_fails_closed(monkeypatch):
    from doclens_ai import rag_runtime

    generator = FakeGenerator()
    monkeypatch.setattr(rag_runtime, "LocalGenerator", lambda _: generator)
    config = settings(
        enabled=True,
        endpoint="http://127.0.0.1/v1/chat/completions",
        model_id="fixture",
        context_window_tokens=128,
        max_output_tokens=64,
    )
    request = AnswerInput(workspace_id=uuid4(), question="Synthetic count?")
    service = rag_runtime.build_rag_runtime(
        SyntheticRetrieval(), config, token_counter=lambda _: 64
    )
    assert (await service.answer(user_id=uuid4(), request=request)).response.answer == "7"
    closed = rag_runtime.build_rag_runtime(SyntheticRetrieval(), config)
    with pytest.raises(GeneratorUnavailable):
        await closed.answer(user_id=uuid4(), request=request)
    assert generator.calls == 1
