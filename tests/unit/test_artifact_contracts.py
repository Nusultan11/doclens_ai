"""Historical artifact routes must not acquire new, unobserved execution pins."""

import json

from doclens_ai.extraction.adapters import adapt_native
from doclens_ai.extraction.engines import default_route
from doclens_ai.extraction.ir_validation import canonical_digest
from doclens_ai.extraction.reconciliation import reconcile
from doclens_ai.services.extraction_artifacts import ExtractionSnapshot
from tests.unit.test_document_ir import provenance, result


def test_historical_route_fingerprint_survives_new_execution_budget_fields():
    observation = adapt_native(result(), provenance=provenance())
    expected = observation.source.model_copy(
        update={"workspace_id": "workspace", "document_version_id": "version"}
    )
    old_route = default_route().model_dump(mode="json")
    old_route["version"] = "1.0"
    old_route.pop("executor_version")
    old_route.pop("execution_budget")
    wire = {
        "artifact_version": "1.0",
        "source": expected.model_dump(mode="json"),
        "route": old_route,
        "observations": [observation.model_dump(mode="json")],
        "reconciled": reconcile((observation,), expected=expected).model_dump(mode="json"),
    }
    restored = ExtractionSnapshot.model_validate_json(json.dumps(wire))
    assert restored.route.fingerprint() == canonical_digest(old_route)
    assert "execution_budget" not in restored.route.model_dump(mode="json")
