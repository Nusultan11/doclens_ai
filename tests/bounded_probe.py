"""Trusted, lightweight subprocess fault fixtures. No model or external service."""

import hashlib
import json
import os
import time

from doclens_ai.extraction.engines import EngineDescriptor
from doclens_ai.extraction.models import DocumentFormat


class ProbeEngine:
    descriptor = EngineDescriptor("probe", "1", "a" * 64, frozenset({DocumentFormat.PDF}))

    def extract(self, source, *, options_json):
        mode = json.loads(options_json).get("mode", "healthy")
        if mode == "hang":
            source.with_suffix(".started").write_text("started")
            while True:
                time.sleep(0.05)
        if mode == "crash":
            os._exit(73)
        if mode == "oom":
            data = bytearray(2 * 1024 * 1024 * 1024)
            return data
        if mode == "cpu":
            source.with_suffix(".started").write_text("started")
            while True:
                pass
        if mode == "touch":
            source.with_suffix(".started").write_text("started")
        from doclens_ai.extraction.ir import DocumentIR, Provenance, SourceIdentity, TextElement
        from doclens_ai.extraction.models import SourceLocation

        payload = source.read_bytes()
        return DocumentIR(
            source=SourceIdentity(
                sha256=hashlib.sha256(payload).hexdigest(),
                size_bytes=len(payload),
                document_format=DocumentFormat.PDF,
            ),
            state="complete",
            elements=(
                TextElement(
                    id="text",
                    source=SourceLocation(page_number=1),
                    text="X" * 128000 if mode == "output" else "bounded fixture",
                    provenance=Provenance(
                        engine="probe",
                        revision="1",
                        implementation_sha256="a" * 64,
                        observation_id="probe",
                    ),
                ),
            ),
        )
