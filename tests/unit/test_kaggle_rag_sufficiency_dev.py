"""ML-14 synthetic pairing and strict capture replay; no inference/network."""

import base64
import copy
import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
R = runpy.run_path(str(ROOT / "tools/kaggle_gpu/rag_sufficiency_dev/benchmark.py"))


def record(case, value=None, *, status=200, finish="stop"):
    if value is None:
        value = {
            "answerable": False,
            "answer": None,
            "citations": [],
            "reason": "insufficient_evidence",
        }
    content = value if isinstance(value, str) else json.dumps(value)
    raw = json.dumps(
        {
            "model": R["MODEL_ALIAS"],
            "choices": [
                {"finish_reason": finish, "message": {"role": "assistant", "content": content}}
            ],
        }
    ).encode()
    return {
        "id": case["id"],
        "request": copy.deepcopy(case["request"]),
        "transport_status": "captured",
        "http_status": status,
        "headers": {"content-type": "application/json"},
        "raw_body_b64": base64.b64encode(raw).decode(),
        "response_bytes": len(raw),
        "elapsed_seconds": 1.0,
    }


def affirmative(case):
    evidence = json.loads(case["request"]["messages"][1]["content"])["evidence"][0]
    quote = evidence["text"][:5]
    return {
        "answerable": True,
        "answer": quote,
        "reason": None,
        "citations": [
            {
                "chunk_id": evidence["chunk_id"],
                "document_version_id": evidence["document_version_id"],
                "quote": quote,
                "quote_start": 0,
                "quote_end": len(quote),
                "answer_start": 0,
                "answer_end": len(quote),
            }
        ],
    }


def report():
    cases = R["frozen_cases"]()
    result = {
        "source_sha256": "synthetic-unit-only",
        "status": "complete",
        "gpu_offload_confirmed": True,
        "runtime_version": R["RUNTIME_COMMIT"],
        "configuration": R["configuration"](),
        "configuration_fingerprint": R["fingerprint"](R["configuration"]()),
        "cases_fingerprint": R["fingerprint"](cases),
        "verified_artifacts": {
            "model_sha256": R["MODEL_SHA256"],
            "runtime_archive_sha256": R["RUNTIME_SHA256"],
            "llama_server_sha256": R["SERVER_SHA256"],
        },
        "responses": [record(c) for c in cases],
    }
    result["responses_fingerprint"] = R["fingerprint"](result["responses"])
    return result


def seal(result):
    result["responses_fingerprint"] = R["fingerprint"](result["responses"])


def test_pairing_seed_labels_and_no_label_leakage():
    from doclens_ai.services.rag import SYSTEM_PROMPT

    cases = R["frozen_cases"]()
    assert cases == R["frozen_cases"]() and len(cases) == 24
    assert R["SYSTEM_PROMPT"] == SYSTEM_PROMPT and R["SEED"] == 42
    assert sum(cases[i]["id"].endswith("/A") for i in range(0, 24, 2)) == 6
    for case in cases:
        user = json.loads(case["request"]["messages"][1]["content"])
        assert set(user) == {"question", "evidence"}
        assert case["request"]["messages"][0]["content"] == SYSTEM_PROMPT
        label = R["labels"]()[case["id"]]
        assert (
            label["split"] == "dev"
            and label["synthetic_fixture"]
            and label["reviewer_status"] == "fixture"
            and label["reviewer_count"] == 0
        )
    assert {c["language"] for c in cases} == {"en", "ru", "kk"}
    assert len({c["category"] for c in cases}) == 6
    assert len({v["source_sha256"] for v in R["labels"]().values()}) == 12


@pytest.mark.parametrize(
    "change", ["text", "question", "prompt", "identity", "seed", "omit", "duplicate", "order"]
)
def test_pair_tampering_rejected(change):
    cases = copy.deepcopy(R["frozen_cases"]())
    case = cases[0]
    if change == "omit":
        cases.pop()
    elif change == "duplicate":
        cases[1] = copy.deepcopy(case)
    elif change == "order":
        cases.reverse()
    elif change == "prompt":
        case["request"]["messages"][0]["content"] = "changed"
    elif change == "seed":
        case["request"]["temperature"] = 0.1
    else:
        user = json.loads(case["request"]["messages"][1]["content"])
        if change == "question":
            user["question"] = "changed"
        elif change == "identity":
            user["evidence"][0]["chunk_id"] = "changed"
        else:
            user["evidence"][0]["text"] += "extra"
        case["request"]["messages"][1]["content"] = json.dumps(user)
    with pytest.raises(ValueError):
        R["validate_pairs"](cases)


def test_model_runtime_configuration_frozen():
    prior = runpy.run_path(str(ROOT / "tools/kaggle_gpu/rag_schema_dev/benchmark.py"))
    for key in (
        "MODEL_REVISION",
        "MODEL_SHA256",
        "RUNTIME_COMMIT",
        "RUNTIME_SHA256",
        "SERVER_SHA256",
        "SETTINGS",
        "SYSTEM_PROMPT",
        "CONTEXT_TOKENS",
    ):
        assert R[key] == prior[key]
    metadata = json.loads(
        (ROOT / "tools/kaggle_gpu/rag_sufficiency_dev/kernel-metadata.json").read_text()
    )
    assert metadata["is_private"] and metadata["enable_gpu"] and not metadata["enable_internet"]
    assert metadata["dataset_sources"] == [R["RUNTIME_DATASET"], R["MODEL_DATASET"]]
    assert metadata["docker_image"] == R["KAGGLE_DOCKER_IMAGE"]


@pytest.mark.parametrize(
    "content,expected",
    [
        ("not JSON", "invalid_json"),
        ('{"answerable":false,"answerable":true}', "invalid_json"),
        (
            {
                "answerable": "false",
                "answer": None,
                "citations": [],
                "reason": "insufficient_evidence",
            },
            "invalid_schema",
        ),
        (
            {
                "answerable": False,
                "answer": "x",
                "citations": [],
                "reason": "insufficient_evidence",
            },
            "invalid_schema",
        ),
        (
            {
                "answerable": False,
                "answer": None,
                "citations": [],
                "reason": "insufficient_evidence",
                "extra": 1,
            },
            "invalid_schema",
        ),
        ({"answerable": True, "answer": "x", "citations": [], "reason": None}, "invalid_schema"),
    ],
)
@pytest.mark.anyio
async def test_invalid_is_not_refusal(content, expected):
    state, _ = await R["replay"](record(R["frozen_cases"]()[0], content))
    assert state == expected


@pytest.mark.parametrize(
    "change", ["foreign", "version", "quote", "range", "duplicate", "coverage"]
)
@pytest.mark.anyio
async def test_citation_failure(change):
    case = R["frozen_cases"]()[0]
    value = affirmative(case)
    citation = value["citations"][0]
    if change == "foreign":
        citation["chunk_id"] = "00000000-0000-0000-0000-000000000099"
    elif change == "version":
        citation["document_version_id"] = "00000000-0000-0000-0000-000000000099"
    elif change == "quote":
        citation["quote"] = "wrong"
    elif change == "range":
        citation["quote_end"] += 10000
    elif change == "duplicate":
        value["citations"] *= 2
    else:
        value["answer"] += "uncited"
    state, output = await R["replay"](record(case, value))
    assert state == "invalid_citation" and output.answerable


@pytest.mark.parametrize("change", ["timeout", "http", "finish", "model", "length"])
@pytest.mark.anyio
async def test_request_failure(change):
    rec = record(R["frozen_cases"]()[0])
    if change == "timeout":
        rec["transport_status"] = "timeout"
    elif change == "http":
        rec["http_status"] = 500
    elif change == "finish":
        rec = record(R["frozen_cases"]()[0], finish="length")
    elif change == "model":
        raw = json.loads(base64.b64decode(rec["raw_body_b64"]))
        raw["model"] = "foreign"
        body = json.dumps(raw).encode()
        rec.update(raw_body_b64=base64.b64encode(body).decode(), response_bytes=len(body))
    else:
        rec["response_bytes"] += 1
        with pytest.raises(ValueError):
            await R["replay"](rec)
        return
    state, output = await R["replay"](rec)
    assert state == "request_failure" and output is None


@pytest.mark.anyio
async def test_metrics_denominators_invalid_diagnostics_and_quality():
    data = report()
    metrics, _ = await R["evaluate"](data, "synthetic-unit-only")
    assert metrics["valid_insufficient_refusals"] == 12 and metrics["false_refusals"] == 12
    assert (
        metrics["planned"] == metrics["attempted"] == 24 and metrics["strict_paired_success"] == 0
    )
    assert (
        metrics["candidate_quality"] == "INCONCLUSIVE"
        and metrics["semantic_correctness"] == "NOT_EVALUATED"
    )
    assert all(c["attempted"] == 4 for c in metrics["categories"].values())
    assert all(c["attempted"] == 8 for c in metrics["languages"].values())
    neg = next(i for i, c in enumerate(R["frozen_cases"]()) if c["id"].endswith("/B"))
    case = R["frozen_cases"]()[neg]
    data["responses"][neg] = record(case, affirmative(case))
    seal(data)
    metrics, _ = await R["evaluate"](data, "synthetic-unit-only")
    assert metrics["unsafe_accepted_negative"] == metrics["raw_affirmative_negative"] == 1
    assert metrics["candidate_quality"] == "REJECT" and not metrics["production_authorized"]
    value = affirmative(case)
    value["citations"][0]["quote"] = "wrong"
    data["responses"][neg] = record(case, value)
    seal(data)
    metrics, _ = await R["evaluate"](data, "synthetic-unit-only")
    assert (
        metrics["unsafe_accepted_negative"] == 0
        and metrics["invalid_citation"] == 1
        and metrics["raw_affirmative_negative"] == 1
    )
    assert metrics["valid_insufficient_refusals"] == 11


@pytest.mark.anyio
async def test_all_request_failures_remain_in_denominators():
    data = report()
    for r in data["responses"]:
        r["transport_status"] = "timeout"
    seal(data)
    metrics, _ = await R["evaluate"](data, "synthetic-unit-only")
    assert metrics["request_failure"] == 24 and metrics["valid_insufficient_refusals"] == 0
    assert metrics["sufficient_denominator"] == metrics["insufficient_denominator"] == 12


@pytest.mark.parametrize(
    "field",
    [
        "source_sha256",
        "configuration_fingerprint",
        "cases_fingerprint",
        "responses_fingerprint",
        "gpu_offload_confirmed",
        "runtime_version",
    ],
)
def test_capture_tampering(field):
    data = report()
    data[field] = "forged" if field != "gpu_offload_confirmed" else False
    with pytest.raises(ValueError):
        R["verify_capture"](data, "synthetic-unit-only")


def test_preregistration_stability_and_wilson():
    assert R["preregistration"]() == R["preregistration"]()
    assert R["preregistration"]()["response_retries"] == R["preregistration"]()["repairs"] == 0
    assert R["wilson"](0, 0) is None
    assert 0 <= R["wilson"](0, 12)[0] < R["wilson"](0, 12)[1] < 1


@pytest.mark.parametrize("outcome", ["malformed", "limit", "timeout"])
@pytest.mark.anyio
async def test_capture_preserves_failure_bytes_without_retries_or_repairs(monkeypatch, outcome):
    import httpx

    calls = []
    original_client = httpx.AsyncClient
    case = R["frozen_cases"]()[0]

    def respond(request):
        calls.append(json.loads(request.content))
        if outcome == "timeout":
            raise httpx.ReadTimeout("synthetic timeout")
        return httpx.Response(
            200,
            headers={"content-type": "application/json", "x-private": "synthetic-marker"},
            stream=httpx.ByteStream(b"not valid JSON"),
        )

    def client(**kwargs):
        return original_client(**kwargs, transport=httpx.MockTransport(respond))

    monkeypatch.setattr(httpx, "AsyncClient", client)
    result = await R["capture"](case, limit=8 if outcome == "limit" else 65536)
    assert calls == [case["request"]]
    assert (
        result["transport_status"]
        == {"malformed": "captured", "limit": "response_limit", "timeout": "timeout"}[outcome]
    )
    expected = (
        b"" if outcome == "timeout" else b"not valid" if outcome == "limit" else b"not valid JSON"
    )
    assert base64.b64decode(result["raw_body_b64"]) == expected
    assert result["response_bytes"] == len(expected)
    assert "synthetic-marker" not in json.dumps(result)
