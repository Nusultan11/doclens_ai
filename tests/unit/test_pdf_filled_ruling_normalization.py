"""Public-only ML-26 fixtures, independently declared boxes and literal oracles."""

from __future__ import annotations

import json
import runpy
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from tools.pdf_table_geometry import filled_ruling_normalization as n

PUBLIC = runpy.run_path(str(Path(__file__).with_name("test_pdf_table_geometry.py")))
ACCEPTED = {"stroke", "filled_rules", "cell_rectangles", "continuous_split", "duplicate_edges"}
EXTRA = (
    "numeric_filled",
    "filled_merged",
    "filled_gap",
    "filled_crossing",
    "thick_shape",
    "square_shape",
    "parallel_overlap",
    "fill_stroke",
    "unsupported_state",
)
VARIANTS = (*PUBLIC["VARIANTS"], *EXTRA)
NUMBERS = ("+001.20 kg", "-0.50 m", "0012", "-12.5 kg")
STROKED_BOXES = (
    (50, 100, 200, 150),
    (200, 100, 350, 150),
    (50, 150, 200, 200),
    (200, 150, 350, 200),
)
FILLED_BOXES = (
    (50.5, 99.5, 200.5, 149.5),
    (200.5, 99.5, 350.5, 149.5),
    (50.5, 149.5, 200.5, 199.5),
    (200.5, 149.5, 350.5, 199.5),
)


def make_fixture(path: Path, variant: str) -> Path:
    """Reuse ML-25 bytes unchanged; extra paths are authored without parser feedback."""
    if variant in PUBLIC["VARIANTS"]:
        return PUBLIC["make_pdf"](path, variant)
    if variant not in EXTRA:
        raise ValueError("unknown_public_fixture")
    PUBLIC["make_pdf"](path, "filled_rules")
    reader = PdfReader(path)
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    data = reader.pages[0].get_contents().get_data().decode("ascii")
    if variant == "numeric_filled":
        for old, new in zip(PUBLIC["LITERALS"], NUMBERS, strict=True):
            data = data.replace(f"({old})", f"({new})")
    elif variant == "filled_merged":
        data = data.replace("200 100 1 101 re f", "200 100 1 50 re f")
    elif variant == "filled_gap":
        data = data.replace("200 100 1 101 re f", "200 100 1 49 re f\n200 151 1 50 re f")
    elif variant == "filled_crossing":
        data = data.replace("1 0 0 1 210 170 Tm", "1 0 0 1 198 170 Tm")
    elif variant == "thick_shape":
        data += "\n70 110 20 10 re f\n"
    elif variant == "square_shape":
        data += "\n70 110 1 1 re f\n"
    elif variant == "parallel_overlap":
        data += "\n50 150.5 301 1 re f\n"
    elif variant == "fill_stroke":
        data = data.replace("re f", "re B")
    elif variant == "unsupported_state":
        data = "q 1 0 0 1 0 0 cm\n" + data + "Q\n"
    stream = DecodedStreamObject()
    stream.set_data(data.encode("ascii"))
    writer.pages[0][NameObject("/Contents")] = writer._add_object(stream)
    with path.open("wb") as output:
        writer.write(output)
    return path


def check_oracle(result: dict, variant: str) -> None:
    """Expected geometry/text is from the drawing, not learned from detector output."""
    if variant not in ACCEPTED | {"numeric_filled"}:
        assert result["status"] == "needs_review" and result["cells"] == []
        assert result["issues"]
        return
    assert result["status"] == "accepted_synthetic" and not result["issues"]
    filled = variant in ("filled_rules", "numeric_filled")
    expected = FILLED_BOXES if filled else STROKED_BOXES
    assert [tuple(c["bounds"]) for c in result["cells"]] == list(expected)
    literals = NUMBERS if variant == "numeric_filled" else PUBLIC["LITERALS"]
    assert [c["text"] for c in result["cells"]] == list(literals)
    indices = [i for c in result["cells"] for i in c["character_indices"]]
    assert sorted(indices) == list(range(len(result["original"]["characters"])))
    assert len(indices) == len(set(indices))
    if filled:
        assert len(result["original"]["detector_cells"]) == 25
        assert len(result["origins"]) == len(result["representation_edges"]) == 6
        for edge in result["representation_edges"]:
            origin = next(
                o for o in result["origins"] if o["object_id"] == edge["source_object_id"]
            )
            x0, top, x1, bottom = origin["bbox"]
            assert origin["paint"] == "f" and origin["fill"] and not origin["stroke"]
            assert edge["derived"]
            assert x0 <= edge["x0"] <= edge["x1"] <= x1
            assert top <= edge["top"] <= edge["bottom"] <= bottom
            assert origin["path_operation"] < origin["paint_operation"]
    else:
        assert len(result["original"]["detector_cells"]) == 4
        assert all(not edge["derived"] for edge in result["representation_edges"])
    for cell in result["cells"]:
        assert all(cell["boundary_edge_indices"])


@pytest.mark.parametrize("variant", VARIANTS)
def test_public_oracles(tmp_path, variant):
    path = make_fixture(tmp_path / f"{variant}.pdf", variant)
    before = path.read_bytes()
    result = n.normalize(path)
    check_oracle(result, variant)
    assert path.read_bytes() == before
    assert result == n.normalize(path)


def test_fixture_bytes_and_fixed_detector(tmp_path):
    from doclens_ai.extraction.pdfplumber_table_candidate import SETTINGS, extract_tables

    settings = dict(SETTINGS)
    for variant in PUBLIC["VARIANTS"]:
        a = make_fixture(tmp_path / "a.pdf", variant)
        b = PUBLIC["make_pdf"](tmp_path / "b.pdf", variant)
        assert a.read_bytes() == b.read_bytes()
    path = make_fixture(tmp_path / "filled.pdf", "filled_rules")
    before = extract_tables(path).to_dict()
    n.normalize(path)
    assert extract_tables(path).to_dict() == before
    assert len(before["grids"]) == 1 and len(before["grids"][0]["cells"]) == 25
    assert SETTINGS == settings


@pytest.mark.parametrize(
    "field",
    [
        "max_file_bytes",
        "max_objects",
        "max_edges",
        "max_characters",
        "max_cells",
        "max_operations",
        "max_stream_bytes",
    ],
)
def test_bounds(tmp_path, field):
    path = make_fixture(tmp_path / "limit.pdf", "filled_rules")
    with pytest.raises(n.diagnose.DiagnosticLimit):
        n.normalize(path, replace(n.Limits(), **{field: 1}))


@pytest.mark.parametrize("value", [0, -1, True, 1.5, float("inf"), float("nan")])
def test_invalid_limits(value):
    with pytest.raises(ValueError):
        n.Limits(max_objects=value)


def test_timeout_and_malformed_input(tmp_path, monkeypatch):
    path = make_fixture(tmp_path / "slow.pdf", "filled_rules")
    ticks = iter([0, 20])
    with monkeypatch.context() as m:
        m.setattr(n.time, "monotonic", lambda: next(ticks))
        with pytest.raises(n.diagnose.DiagnosticLimit, match="timeout"):
            n.normalize(path)
    path.write_bytes(b"public malformed")
    from pypdf.errors import PdfReadError

    with pytest.raises(PdfReadError):
        n.normalize(path)


@pytest.mark.parametrize("failure", ["timeout", "memory_limit", "output_limit", "worker_failed"])
def test_parent_failure_cleanup(tmp_path, failure):
    from tools.docx_footnote_candidate.benchmark import monitor

    command = "import time; time.sleep(10)"
    guards = dict(n.GUARDS)
    if failure == "timeout":
        guards["timeout_seconds"] = 0.05
    elif failure == "memory_limit":
        guards["max_process_bytes"] = 1
    elif failure == "output_limit":
        (tmp_path / "large.capture").write_bytes(b"x" * 100)
        guards["max_capture_bytes"] = 10
    else:
        command = "raise SystemExit(4)"
    resource = monitor([sys.executable, "-B", "-c", command], tmp_path, guards=guards)
    assert resource["failure"] == failure and resource["cleanup"]
    assert n.collect(tmp_path, resource, "unknown") is None
    assert not (tmp_path / "result.json").exists()


@pytest.mark.parametrize("value", [None, [], {}, {"version": n.VERSION}, "incomplete"])
def test_invalid_output_not_published(tmp_path, value):
    capture = tmp_path / "result.capture"
    capture.write_text(json.dumps(value), encoding="utf-8")
    assert n.collect(tmp_path, {"failure": None, "cleanup": True}, "unknown") is None
    assert not capture.exists() and not (tmp_path / "result.json").exists()


def test_output_bound_and_provenance(tmp_path):
    path = make_fixture(tmp_path / "a.pdf", "filled_rules")
    value = n.normalize(path)
    capture = tmp_path / "result.capture"
    with pytest.raises(n.diagnose.DiagnosticLimit):
        n.diagnose.write_capture(capture, value, max_bytes=10)
    assert n.collect(tmp_path, {"failure": "worker_failed", "cleanup": True}, n.sha(path)) is None
    n.diagnose.write_capture(capture, value)
    assert n.collect(tmp_path, {"failure": None, "cleanup": True}, "wrong_source") is None
    n.diagnose.write_capture(capture, value)
    assert n.collect(tmp_path, {"failure": None, "cleanup": True}, n.sha(path)) == json.loads(
        json.dumps(value)
    )
    assert (tmp_path / "result.json").exists()


def test_cli_success_failure_and_existing_output(tmp_path):
    source = make_fixture(tmp_path / "public.pdf", "filled_rules")
    output = tmp_path / "success"
    command = [
        sys.executable,
        "-B",
        str(Path(n.__file__).resolve()),
        "--input",
        str(source),
        "--output",
        str(output),
    ]
    run = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert run.returncode == 0 and json.loads(run.stdout)["execution"] == "PASS"
    value = json.loads((output / "result.json").read_text())
    check_oracle(value, "filled_rules")
    before = (output / "result.json").read_bytes()
    rerun = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert rerun.returncode == 2 and (output / "result.json").read_bytes() == before
    source.write_bytes(b"malformed public PDF")
    command[-1] = str(tmp_path / "failure")
    failed = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert failed.returncode == 1
    assert not (tmp_path / "failure/result.json").exists()
    assert not (tmp_path / "failure/result.capture").exists()
