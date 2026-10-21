"""Synthetic contracts only; no Corpus v1/Gold text or real OCR dependency."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from doclens_ai.extraction.fidelity_gold import Locator
from doclens_ai.extraction.models import ExtractionStatus, SourceLocation, TextBlock
from doclens_ai.extraction.parsers import extract_file
from tools.pdf_ocr_candidate import benchmark as ocr


def pdf(path: Path, texts: list[str]) -> Path:
    writer = PdfWriter()
    font = writer._add_object(
        DictionaryObject(
            {  # noqa: SLF001
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    for text in texts:
        page = writer.add_blank_page(612, 792)
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
            }
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)  # noqa: SLF001
    writer.write(path)
    return path


RUNTIME = ocr.Runtime("not-installed", "not-installed", "no-models")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", True),
        (" \n\t", True),
        ("1.00", True),
        ("a" * 19, True),
        ("a" * 20, False),
        ("0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9", False),
    ],
)
def test_selection(text: str, expected: bool) -> None:
    assert ocr.eligible(text, ocr.Limits()) is expected


def test_mixed_native_and_ocr_preserve_numeric_and_page(tmp_path, monkeypatch) -> None:
    source = pdf(tmp_path / "mixed.pdf", ["Native evidence 001.20 kg version 2.0", "", ""])
    native = extract_file(source)
    called = []

    def fake(path, page, runtime, limits, work):
        called.append(page)
        return "Recovered 0007.50 kg -3.0 12/08/2026", {"page": page, "state": "ocr"}

    monkeypatch.setattr(ocr, "ocr_page", fake)
    result, pages = ocr.selective_extract(source, RUNTIME, ocr.Limits(), tmp_path)
    assert called == [2, 3]
    assert result.blocks[0] == native.blocks[0]
    recovered = [b for b in result.blocks if b.text.startswith("Recovered")]
    assert [b.source for b in recovered] == [
        SourceLocation(page_number=2),
        SourceLocation(page_number=3),
    ]
    assert [b.text for b in recovered] == ["Recovered 0007.50 kg -3.0 12/08/2026"] * 2
    assert result.status is ExtractionStatus.NEEDS_REVIEW
    assert pages[0] == {"page": 1, "state": "native"}
    assert [b.order for b in result.blocks] == list(range(len(result.blocks)))


def test_no_runtime_needed_for_sufficient_native(tmp_path, monkeypatch) -> None:
    path = pdf(tmp_path / "native.pdf", ["All native text remains completely unchanged 123.45"])
    monkeypatch.setattr(ocr, "ocr_page", lambda *args: pytest.fail("Unexpected OCR"))
    actual, pages = ocr.selective_extract(path, RUNTIME, ocr.Limits(), tmp_path)
    assert actual == extract_file(path)
    assert pages == [{"page": 1, "state": "native"}]


@pytest.mark.parametrize("text", ["", " \n", "12345\n"])
def test_empty_or_exact_duplicate_ocr_is_not_appended(tmp_path, monkeypatch, text) -> None:
    path = pdf(tmp_path / "short.pdf", ["12345"])
    monkeypatch.setattr(ocr, "ocr_page", lambda *args: (text, {"page": 1, "state": "ocr"}))
    result, _ = ocr.selective_extract(path, RUNTIME, ocr.Limits(), tmp_path)
    assert len(result.blocks) == 1
    assert result.blocks[0].text == extract_file(path).blocks[0].text
    assert result.status is ExtractionStatus.NEEDS_REVIEW


@pytest.mark.parametrize(
    "failure",
    ["timeout", "memory_limit", "output_limit", "missing_runtime", "tool_failed", "missing_ocr"],
)
def test_page_failure_does_not_discard_native_or_other_pages(
    tmp_path, monkeypatch, failure
) -> None:
    path = pdf(
        tmp_path / "failure.pdf", ["", "Native text still available after a failed page.", ""]
    )

    def fake(path, page, runtime, limits, work):
        if page == 1:
            raise ocr.BoundedFailure(failure)
        return "Recovered later", {"page": page, "state": "ocr"}

    monkeypatch.setattr(ocr, "ocr_page", fake)
    result, pages = ocr.selective_extract(path, RUNTIME, ocr.Limits(), tmp_path)
    assert pages[0]["state"] == failure
    assert result.status is ExtractionStatus.NEEDS_REVIEW
    assert any(
        b.text.startswith("Native text") and b.source.page_number == 2 for b in result.blocks
    )
    assert any(b.text == "Recovered later" and b.source.page_number == 3 for b in result.blocks)


def test_malformed_pdf_remains_failed(tmp_path) -> None:
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"%PDF-1.7\nmalformed")
    actual, pages = ocr.selective_extract(path, RUNTIME, ocr.Limits(), tmp_path)
    assert actual.status is ExtractionStatus.FAILED
    assert pages == []
    assert ocr.restore(actual.to_dict()) == actual


def test_page_pixel_and_character_limits(tmp_path, monkeypatch) -> None:
    path = pdf(tmp_path / "limits.pdf", ["", ""])
    monkeypatch.setattr(
        ocr, "ocr_page", lambda *args: ("x" * 30, {"page": args[1], "state": "ocr"})
    )
    result, pages = ocr.selective_extract(
        path, RUNTIME, replace(ocr.Limits(), max_characters=10), tmp_path
    )
    assert [p["state"] for p in pages] == ["output_limit", "output_limit"]
    assert not any(b.text for b in result.blocks)
    _, pages = ocr.selective_extract(path, RUNTIME, replace(ocr.Limits(), max_pixels=1), tmp_path)
    assert [p["state"] for p in pages] == ["pixel_limit", "pixel_limit"]
    _, pages = ocr.selective_extract(
        path, RUNTIME, replace(ocr.Limits(), max_ocr_pages=0), tmp_path
    )
    assert [p["state"] for p in pages] == ["page_limit", "page_limit"]


def test_ocr_budget_reserves_all_later_native_text(tmp_path, monkeypatch) -> None:
    path = pdf(tmp_path / "reserve.pdf", ["", "1234567890"])
    native = extract_file(path)
    native_length = sum(len(block.text) for block in native.blocks)
    monkeypatch.setattr(ocr, "ocr_page", lambda *args: ("extra", {"page": args[1], "state": "ocr"}))
    result, pages = ocr.selective_extract(
        path, RUNTIME, replace(ocr.Limits(), max_characters=native_length), tmp_path
    )
    assert sum(len(block.text) for block in result.blocks) <= native_length
    assert pages[0]["state"] == "output_limit"
    assert all(
        any(b.text == n.text and b.source == n.source for b in result.blocks) for n in native.blocks
    )


@pytest.mark.parametrize(
    ("case", "failure"),
    [
        ("exact", None),
        ("overflow", None),
        ("empty", None),
        ("failed", "timeout"),
        ("failed", "missing_ocr"),
        ("failed", "memory_limit"),
    ],
)
def test_combined_output_budget_boundaries(tmp_path, monkeypatch, case, failure) -> None:
    path = pdf(tmp_path / "boundary.pdf", ["", "Native 001.20 kg remains sufficient."])
    native = extract_file(path)
    native_size = sum(len(block.text) for block in native.blocks)
    additional = "OCR 009.50 kg" if case in {"exact", "overflow"} else ""
    budget = native_size + len(additional) - (case == "overflow")

    def fake(path, page, runtime, limits, work):
        assert page == 1
        if failure:
            raise ocr.BoundedFailure(failure)
        return additional, {"page": page, "state": "ocr" if additional else "empty_ocr"}

    monkeypatch.setattr(ocr, "ocr_page", fake)
    result, pages = ocr.selective_extract(
        path, RUNTIME, replace(ocr.Limits(), max_characters=budget), tmp_path
    )
    assert result.status is ExtractionStatus.NEEDS_REVIEW
    assert sum(len(block.text) for block in result.blocks) <= budget
    assert all(
        sum(b.text == n.text and b.source == n.source for b in result.blocks) == 1
        for n in native.blocks
    )
    assert [b.order for b in result.blocks] == list(range(len(result.blocks)))
    assert pages[1] == {"page": 2, "state": "native"}
    if case == "exact":
        assert sum(len(block.text) for block in result.blocks) == budget
        assert result.blocks[1].text == additional
        assert result.blocks[1].source == SourceLocation(page_number=1)
        assert result.blocks[2].text == native.blocks[1].text
        assert result.blocks[2].source == native.blocks[1].source
        assert pages[0]["state"] == "ocr"
    else:
        assert result.blocks == native.blocks
        expected = failure or ("output_limit" if case == "overflow" else "empty_ocr")
        assert pages[0]["state"] == expected


@pytest.mark.parametrize(
    ("data", "category"),
    [
        (b"P5\n2 2\n255\n\x00\x00\x00\x00", None),
        (b"P5\n2 2\n255\n\xff\xff\xff\xff", None),
        (b"P6\n1 1\n255\n000", "invalid_render"),
        (b"P5\n2 2\n255\n0", "invalid_render"),
        (b"P5\n999999 999999\n255\n", "pixel_limit"),
    ],
)
def test_render_validation(tmp_path, data, category) -> None:
    path = tmp_path / "page.pgm"
    path.write_bytes(data)
    if category:
        with pytest.raises(ocr.BoundedFailure, match=category):
            ocr.pgm_ink(path, ocr.Limits())
    else:
        assert ocr.pgm_ink(path, ocr.Limits()) in (0, 1)


@pytest.mark.parametrize("blank", [False, True])
def test_tool_arguments_real_page_and_cleanup(tmp_path, monkeypatch, blank) -> None:
    calls = []

    def fake(args, work, limits):
        calls.append(args)
        if args[0] == RUNTIME.renderer and len(calls) == 1:
            Path(args[-1] + ".pgm").write_bytes(
                b"P5\n2 2\n255\n" + (b"\xff" if blank else b"\x00") * 4
            )
        else:
            Path(args[2] + ".txt").write_text("009.50 kg", encoding="utf-8")
        return {"exit_code": 0}

    monkeypatch.setattr(ocr, "command", fake)
    text, observation = ocr.ocr_page(Path("not-read.pdf"), 7, RUNTIME, ocr.Limits(), tmp_path)
    assert calls[0][1:5] == ["-f", "7", "-l", "7"]
    assert observation["page"] == 7
    assert len(calls) == (1 if blank else 2)
    assert text == ("" if blank else "009.50 kg")
    assert list(tmp_path.iterdir()) == []


def test_wrong_page_text_cannot_pass_provenance(tmp_path) -> None:
    path = pdf(tmp_path / "wrong.pdf", ["", ""])
    native = extract_file(path)
    result = replace(
        native,
        blocks=(*native.blocks, TextBlock(2, "Synthetic 123.45", SourceLocation(page_number=2))),
    )
    record = SimpleNamespace(
        source_sha256=native.source_sha256,
        source_size_bytes=native.source_size_bytes,
        document_format="pdf",
        order_pairs=[],
        table_cells=[],
        table_relationships=[],
        cells=[],
        anchors=[
            SimpleNamespace(
                anchor_id="a1",
                text="Synthetic 123.45",
                source=Locator(region="body", page_number=1),
                occurrence=1,
            )
        ],
    )
    score = ocr.summarize(record, {"result": result.to_dict(), "failure": None})
    assert score["hits"] == {"a1": True}
    assert score["located"] == {"a1": False}
    assert score["scores"]["metrics"]["provenance"]["passed"] == 0
    assert "Synthetic" not in json.dumps(score)


@pytest.mark.parametrize(
    ("rss", "elapsed", "disk", "expected"),
    [
        (2, 2, 2, "memory_limit"),
        (0, 2, 2, "timeout"),
        (0, 0, 2, "output_limit"),
        (1, 1, 1, None),
    ],
)
def test_resource_precedence(rss, elapsed, disk, expected) -> None:
    limits = replace(ocr.Limits(), max_process_bytes=1, timeout_seconds=1, max_scratch_bytes=1)
    assert ocr.guard_reason(rss, elapsed, disk, limits) == expected


def test_missing_command_exception_sanitized(tmp_path) -> None:
    with pytest.raises(ocr.BoundedFailure) as error:
        ocr.command([str(tmp_path / "private-secret-missing.exe")], tmp_path, ocr.Limits())
    assert str(error.value) == "missing_runtime"
    assert "private-secret" not in str(error.value)


@pytest.mark.parametrize("failure", ["timeout", "memory_limit", "output_limit"])
def test_actual_subprocess_resource_termination(tmp_path, failure) -> None:
    limits = ocr.Limits()
    code = "import time;time.sleep(5)"
    if failure == "timeout":
        limits = replace(limits, tool_timeout_seconds=0.05)
    elif failure == "memory_limit":
        limits = replace(limits, max_process_bytes=1)
    else:
        code = (
            "from pathlib import Path;import time;"
            "Path('large').write_bytes(b'x'*100000);time.sleep(5)"
        )
        # Use the scratch path explicitly; command does not change process cwd.
        code = code.replace("Path('large')", f"Path({str(tmp_path / 'large')!r})")
        limits = replace(limits, max_scratch_bytes=100)
    with pytest.raises(ocr.BoundedFailure, match=failure):
        ocr.command([sys.executable, "-c", code], tmp_path, limits)


@pytest.mark.parametrize("failure", [None, "memory_limit", "timeout"])
def test_isolated_worker_capture_or_unknown_on_termination(tmp_path, failure) -> None:
    source = pdf(tmp_path / "source.pdf", ["Sufficient ordinary native evidence 123.45"])
    limits = ocr.Limits()
    if failure == "memory_limit":
        limits = replace(limits, max_process_bytes=1)
    elif failure == "timeout":
        limits = replace(limits, timeout_seconds=0)
    capture = ocr.isolated(source, RUNTIME, limits, tmp_path / "capture", candidate=False)
    assert capture["failure"] == failure
    assert capture["runtime"]["cleanup"] is True
    if failure:
        assert capture["result"] is None
        assert ocr.summarize(None, capture)["scores"] is None
    else:
        assert ocr.restore(capture["result"]) == extract_file(source)


@pytest.mark.parametrize("reap_root", [True, False])
def test_tree_cleanup_leaves_multiprocessing_root_for_its_owner(monkeypatch, reap_root) -> None:
    import psutil

    killed, waited = [], []
    descendant = SimpleNamespace(kill=lambda: killed.append("descendant"))
    root = SimpleNamespace(
        children=lambda **kw: [descendant], kill=lambda: killed.append("root")
    )
    monkeypatch.setattr(psutil, "Process", lambda pid: root)

    def wait(processes, timeout):
        waited.extend(processes)
        return processes, []

    monkeypatch.setattr(psutil, "wait_procs", wait)
    assert ocr.stop_tree(123, reap_root=reap_root) is True
    assert set(killed) == {"root", "descendant"}
    assert any(process is descendant for process in waited)
    assert any(process is root for process in waited) is reap_root


@pytest.mark.parametrize("case", ["joined", "kill_fallback", "still_running", "descendant_alive"])
def test_isolated_never_closes_live_worker_or_accepts_failed_cleanup(tmp_path, monkeypatch, case):
    events = []

    class Child:
        pid = 123
        alive = True

        def start(self):
            # A completed payload cannot override a resource/cleanup failure.
            (output / "result.json").write_text(
                '{"result": {"untrusted": true}, "pages": []}'
            )

        def is_alive(self):
            return self.alive

        def join(self, timeout):
            events.append("join")

        def kill(self):
            events.append("kill")
            self.alive = case == "still_running"

        def close(self):
            assert not self.alive and "join" in events
            events.append("close")

    child = Child()

    def stop(pid, *, reap_root):
        assert pid == child.pid and reap_root is False
        events.append("stop")
        child.alive = case in {"kill_fallback", "still_running"}
        return case != "descendant_alive"

    monkeypatch.setattr(
        ocr.multiprocessing, "get_context", lambda _: SimpleNamespace(Process=lambda **kw: child)
    )
    monkeypatch.setattr(ocr, "tree_rss", lambda pid: 0)
    monkeypatch.setattr(ocr, "stop_tree", stop)
    output = tmp_path / "capture"
    capture = ocr.isolated(
        tmp_path / "source.pdf", RUNTIME, replace(ocr.Limits(), timeout_seconds=0),
        output, candidate=False,
    )
    failed = case in {"still_running", "descendant_alive"}
    assert capture["runtime"]["cleanup"] is not failed
    assert capture["failure"] == ("cleanup_failed" if failed else "timeout")
    assert capture["result"] is None
    assert ("close" in events) is (case != "still_running")
    if case in {"kill_fallback", "still_running"}:
        assert events[:4] == ["stop", "join", "kill", "join"]


def test_output_directory_must_be_ignored(tmp_path) -> None:
    with pytest.raises(ValueError, match="ignored"):
        ocr.ignored(Path("docs/eda/not-an-output-directory"))


def test_custom_raw_directory_is_also_protected(tmp_path) -> None:
    with pytest.raises(ValueError, match="RAW"):
        ocr.ignored(tmp_path / "out", corpus=tmp_path)
