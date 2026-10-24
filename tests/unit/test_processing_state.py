from datetime import timedelta
from types import SimpleNamespace

import pytest

from doclens_ai.chunking.ir import IR_CHUNKER_VERSION
from doclens_ai.extraction.engines import EngineRoute, default_route
from doclens_ai.services.processing import (
    InvalidProcessingTransition,
    ProcessingPolicy,
    _require_current_ir_publication,
    default_processing_configuration_fingerprint,
)


def test_current_ir_publication_requires_consistent_current_chunk_provenance():
    route = EngineRoute(
        engines=default_route().engines,
        runtime_manifest_json=default_route().runtime_manifest_json,
        mode="verified_ir",
        chunker_version=IR_CHUNKER_VERSION,
    )
    run = SimpleNamespace(extraction_route=route.model_dump(mode="json"))
    _require_current_ir_publication(run, (IR_CHUNKER_VERSION,))
    for versions in [(), ("2.0",), (IR_CHUNKER_VERSION, "2.0")]:
        with pytest.raises(InvalidProcessingTransition, match="complete current IR evidence"):
            _require_current_ir_publication(run, versions)
    for change in [{"validator_version": "2.0"}, {"chunker_version": "2.0"}, {"version": "1.1"}]:
        old = SimpleNamespace(extraction_route=run.extraction_route | change)
        with pytest.raises(InvalidProcessingTransition, match="complete current IR evidence"):
            _require_current_ir_publication(old, (IR_CHUNKER_VERSION,))


@pytest.mark.parametrize("route", [None, {"mode": "native", "version": "1.0"}])
def test_historical_native_publication_contract_is_preserved(route):
    _require_current_ir_publication(SimpleNamespace(extraction_route=route), ("1.3",))


def test_default_processing_configuration_fingerprint_is_stable() -> None:
    first = default_processing_configuration_fingerprint()
    assert len(first) == 64
    assert first == default_processing_configuration_fingerprint()


def test_contract_runtime_change_invalidates_processing_configuration(monkeypatch):
    from doclens_ai.extraction import runtime

    original = default_processing_configuration_fingerprint()
    installed_version = runtime.version
    monkeypatch.setattr(
        runtime,
        "version",
        lambda name: "changed" if name == "pydantic" else installed_version(name),
    )
    assert default_processing_configuration_fingerprint() != original


def test_processing_identity_changes_with_parser_code_and_versions(monkeypatch) -> None:
    from doclens_ai.extraction import runtime

    original = default_processing_configuration_fingerprint()
    monkeypatch.setitem(runtime.PARSER_VERSIONS, "pypdf", "different")
    assert default_processing_configuration_fingerprint() != original
    monkeypatch.undo()
    monkeypatch.setattr(runtime, "IMPLEMENTATION_FILES", ("extraction/models.py",))
    assert default_processing_configuration_fingerprint() != original


def test_retry_backoff_is_exponential_and_bounded() -> None:
    policy = ProcessingPolicy(
        retry_base_delay=timedelta(seconds=10),
        retry_max_delay=timedelta(seconds=25),
    )

    assert policy.retry_delay(1) == timedelta(seconds=10)
    assert policy.retry_delay(2) == timedelta(seconds=20)
    assert policy.retry_delay(3) == timedelta(seconds=25)
    assert policy.retry_delay(100) == timedelta(seconds=25)


@pytest.mark.parametrize(
    "policy",
    [
        ProcessingPolicy(lease_duration=timedelta(seconds=1)),
        ProcessingPolicy(retry_base_delay=timedelta(seconds=1)),
    ],
)
def test_valid_processing_policy_is_accepted(policy: ProcessingPolicy) -> None:
    assert policy.lease_duration > timedelta(0)


def test_invalid_processing_policy_is_rejected() -> None:
    with pytest.raises(ValueError, match="lease duration"):
        ProcessingPolicy(lease_duration=timedelta(0))
    with pytest.raises(ValueError, match="retry max"):
        ProcessingPolicy(
            retry_base_delay=timedelta(seconds=2),
            retry_max_delay=timedelta(seconds=1),
        )
    with pytest.raises(ValueError, match="attempt count"):
        ProcessingPolicy().retry_delay(0)
