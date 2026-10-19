"""Offline OOXML ancillary evidence; never extends or replaces production output.

Paths are XML child ordinals, not rendered coordinates. Gold part_index is unknown.
Private text/part names belong only in memory or explicitly ignored local captures.
"""

from __future__ import annotations

import hashlib
import posixpath
import re
import stat
import time
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

from doclens_ai.extraction.models import ExtractionStatus

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"
VERSION = "docx-footnotes-offline-v1"


@dataclass(frozen=True, slots=True)
class FootnoteLimits:
    max_file_bytes: int = 50 * 1024**2
    max_entries: int = 20_000
    max_entry_bytes: int = 16 * 1024**2
    max_expanded_bytes: int = 128 * 1024**2
    max_ratio: int = 200
    max_nodes: int = 200_000
    max_depth: int = 128
    max_notes: int = 1_000
    max_references: int = 10_000
    max_paragraphs: int = 5_000
    max_characters: int = 500_000
    timeout_seconds: float = 15.0

    def __post_init__(self) -> None:
        if (
            any(
                type(v) is not int or v <= 0
                for k, v in asdict(self).items()
                if k != "timeout_seconds"
            )
            or type(self.timeout_seconds) not in (int, float)
            or not 0 < self.timeout_seconds < float("inf")
        ):
            raise ValueError("Invalid offline limits")


@dataclass(frozen=True, slots=True)
class FootnoteReference:
    """One actual reference, including repeated references to the same note."""

    ordinal: int
    note_id: str
    body_xml_path: tuple[int, ...]
    paragraph_xml_path: tuple[int, ...] | None
    body_child_index: int
    baseline_block_index: int | None
    supported_context: bool


@dataclass(frozen=True, slots=True)
class NoteParagraph:
    child_index: int
    text: str
    hyperlink_relationship_ids: tuple[str, ...]
    complete: bool


@dataclass(frozen=True, slots=True)
class FootnoteEvidence:
    part_uri: str
    note_id: str
    note_element_index: int
    paragraphs: tuple[NoteParagraph, ...]
    reference_ordinals: tuple[int, ...]
    complete: bool
    gold_part_index: None = None


@dataclass(frozen=True, slots=True)
class AncillaryEvidence:
    status: ExtractionStatus
    source_sha256: str | None = None
    source_size_bytes: int | None = None
    main_part_uri: str | None = None
    footnote_part_uri: str | None = None
    footnote_relationship_id: str | None = None
    notes: tuple[FootnoteEvidence, ...] = ()
    references: tuple[FootnoteReference, ...] = ()
    issues: tuple[str, ...] = ()
    schema_version: Literal["docx-footnotes-offline-v1"] = field(default=VERSION, init=False)

    def to_dict(self) -> dict:
        return asdict(self)


class _Failure(Exception):
    pass


def _id(value: str | None) -> int:
    if value is None or not re.fullmatch(r"[+-]?[0-9]{1,10}", value):
        raise _Failure("invalid_note_id")
    return int(value)


def _target(source: str, target: str) -> str:
    url = urlsplit(target)
    if url.scheme or url.netloc or url.query or url.fragment:
        raise _Failure("invalid_relationship")
    value = unquote(url.path)
    if not value or any(c in value for c in ("\\", "\x00", ":")):
        raise _Failure("invalid_relationship")
    name = posixpath.normpath(
        value.lstrip("/")
        if value.startswith("/")
        else posixpath.join(posixpath.dirname(source), value)
    )
    if name in (".", "..") or name.startswith("../"):
        raise _Failure("invalid_relationship")
    return name


def _rels_name(part: str) -> str:
    return posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")


def _walk(root: ET.Element, tick):
    stack = [(root, (), None, True)]
    while stack:
        node, path, paragraph, supported = stack.pop()
        tick()
        if node.tag == W + "p":
            paragraph = path
        if node.tag in {W + t for t in ("del", "ins", "sdt", "txbxContent", "drawing", "pict")}:
            supported = False
        yield node, path, paragraph, supported
        stack.extend(
            (child, path + (i,), paragraph, supported)
            for i, child in reversed(list(enumerate(node)))
        )


def _paragraph(root: ET.Element, relationships: dict, tick) -> tuple[str, tuple[str, ...], bool]:
    chunks, links = [], []
    complete = True
    stack = [root]
    containers = {W + t for t in ("p", "r", "hyperlink")}
    ignore = {
        W + t
        for t in (
            "pPr",
            "rPr",
            "footnoteRef",
            "bookmarkStart",
            "bookmarkEnd",
            "proofErr",
            "permStart",
            "permEnd",
        )
    }
    controls = {
        W + "tab": "\t",
        W + "br": "\n",
        W + "cr": "\n",
        W + "noBreakHyphen": "\u2011",
        W + "softHyphen": "\u00ad",
    }
    while stack:
        tick()
        node = stack.pop()
        if node.tag == W + "t":
            chunks.append(node.text or "")
        elif node.tag in controls:
            chunks.append(controls[node.tag])
        elif node.tag in ignore:
            continue
        elif node.tag in containers:
            if node.tag == W + "hyperlink":
                rid = node.get("{" + REL[:-1] + "}id")
                if rid:
                    links.append(rid)
                    if rid not in relationships or relationships[rid][1] != REL + "hyperlink":
                        complete = False
                elif not node.get(W + "anchor"):
                    complete = False
            stack.extend(reversed(list(node)))
        else:
            complete = False  # Never flatten tables, fields, revisions or drawings.
    return "".join(chunks), tuple(links), complete


def extract_footnotes(
    source: str | Path, *, limits: FootnoteLimits | None = None
) -> AncillaryEvidence:
    """Read package relationships without executing Office or mutating RAW.

    Any fatal error discards all partial evidence. Ordinary unsupported note
    structures retain explicitly incomplete paragraphs and a needs_review status.
    The caller must isolate this logical parser for hard time/RSS enforcement.
    """
    active = limits or FootnoteLimits()
    started = time.monotonic()
    digest, size = None, None

    def tick() -> None:
        if time.monotonic() - started >= active.timeout_seconds:
            raise _Failure("timeout")

    try:
        path = Path(source)
        if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".docx":
            raise _Failure("invalid_source")
        size = path.stat().st_size
        if not 0 < size <= active.max_file_bytes:
            raise _Failure("input_limit")
        h = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024**2), b""):
                tick()
                h.update(chunk)
        digest = h.hexdigest()
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if (
                len(entries) > active.max_entries
                or sum(e.file_size for e in entries) > active.max_expanded_bytes
            ):
                raise _Failure("archive_limit")
            names = set()
            for entry in entries:
                tick()
                name = entry.filename
                if (
                    name.lower() in names
                    or "\\" in name
                    or name.startswith("/")
                    or any(p in ("..", ".") for p in name.rstrip("/").split("/"))
                    or ":" in name
                ):
                    raise _Failure("invalid_archive")
                names.add(name.lower())
                if entry.flag_bits & 1 or stat.S_ISLNK(entry.external_attr >> 16):
                    raise _Failure("invalid_archive")
                if (
                    entry.file_size > active.max_entry_bytes
                    or entry.file_size / max(1, entry.compress_size) > active.max_ratio
                ):
                    raise _Failure("archive_limit")
                if entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise _Failure("unsupported_compression")
            node_count = 0

            def xml(name: str) -> ET.Element:
                nonlocal node_count
                tick()
                data = archive.read(name)
                if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)\b", data.replace(b"\x00", b""), re.I):
                    raise _Failure("invalid_xml")
                root = ET.fromstring(data)
                stack = [(root, 1)]
                while stack:
                    node, depth = stack.pop()
                    tick()
                    node_count += 1
                    if node_count > active.max_nodes or depth > active.max_depth:
                        raise _Failure("xml_limit")
                    stack.extend((c, depth + 1) for c in node)
                return root

            def relationships(name: str, required: bool = False) -> dict:
                if name not in archive.namelist() and not required:
                    return {}
                root = xml(name)
                if root.tag != PKG + "Relationships":
                    raise _Failure("invalid_relationship")
                result = {}
                for child in root:
                    key, target, kind = (child.get(k) for k in ("Id", "Target", "Type"))
                    mode = child.get("TargetMode", "Internal")
                    if (
                        child.tag != PKG + "Relationship"
                        or not key
                        or key in result
                        or not target
                        or not kind
                        or mode not in ("Internal", "External")
                    ):
                        raise _Failure("invalid_relationship")
                    result[key] = (target, kind, mode)
                return result

            xml("[Content_Types].xml")
            package = relationships("_rels/.rels", required=True)
            main_links = [v for v in package.values() if v[1] == REL + "officeDocument"]
            if len(main_links) != 1 or main_links[0][2] != "Internal":
                raise _Failure("invalid_main_relationship")
            main = _target("", main_links[0][0])
            document = xml(main)
            if document.tag != W + "document":
                raise _Failure("unsupported_document_namespace")
            body = document.find(W + "body")
            if body is None:
                raise _Failure("missing_body")
            refs = []
            block_indices = {}
            for i, child in enumerate(body):
                if child.tag in (W + "p", W + "tbl"):
                    block_indices[i] = len(block_indices)
            for node, address, paragraph, supported in _walk(body, tick):
                if node.tag == W + "footnoteReference":
                    _id(node.get(W + "id"))
                    top = address[0]
                    refs.append(
                        FootnoteReference(
                            len(refs),
                            node.get(W + "id"),
                            address,
                            paragraph,
                            top,
                            block_indices.get(top),
                            supported and top in block_indices,
                        )
                    )
                    if len(refs) > active.max_references:
                        raise _Failure("reference_limit")
            main_rels = relationships(_rels_name(main))
            note_links = [(k, v) for k, v in main_rels.items() if v[1] == REL + "footnotes"]
            if not note_links:
                if refs:
                    raise _Failure("missing_footnote_relationship")
                return AncillaryEvidence(ExtractionStatus.SUCCESS, digest, size, "/" + main)
            if len(note_links) != 1 or note_links[0][1][2] != "Internal":
                raise _Failure("invalid_footnote_relationship")
            rid, relation = note_links[0]
            part = _target(main, relation[0])
            root = xml(part)
            if root.tag != W + "footnotes":
                raise _Failure("invalid_footnotes")
            note_rels = relationships(_rels_name(part))
            issues, notes, seen, excluded = set(), [], set(), set()
            paragraphs, characters = 0, 0
            for i, node in enumerate(root):
                tick()
                if node.tag != W + "footnote":
                    issues.add("unsupported_note_element")
                    continue
                key = _id(node.get(W + "id"))
                if key in seen:
                    raise _Failure("duplicate_note_id")
                seen.add(key)
                kind = node.get(W + "type", "normal")
                if kind in ("separator", "continuationSeparator", "continuationNotice"):
                    excluded.add(key)
                    continue
                if len(notes) >= active.max_notes:
                    raise _Failure("note_limit")
                linked = tuple(r.ordinal for r in refs if _id(r.note_id) == key)
                complete = bool(linked) and key >= 0 and kind == "normal"
                if not linked:
                    issues.add("unreferenced_note")
                if key < 0 or kind != "normal":
                    issues.add("unsupported_note_type")
                content = []
                for j, child in enumerate(node):
                    tick()
                    if child.tag != W + "p":
                        complete = False
                        issues.add("unsupported_note_structure")
                        continue
                    text, links, supported = _paragraph(child, note_rels, tick)
                    content.append(NoteParagraph(j, text, links, supported))
                    paragraphs += 1
                    characters += len(text)
                    if paragraphs > active.max_paragraphs or characters > active.max_characters:
                        raise _Failure("output_limit")
                    if not supported:
                        complete = False
                        issues.add("unsupported_paragraph")
                if not content:
                    complete = False
                    issues.add("empty_note")
                notes.append(
                    FootnoteEvidence(
                        "/" + part, node.get(W + "id"), i, tuple(content), linked, complete
                    )
                )
            if any(_id(r.note_id) not in seen for r in refs):
                issues.add("dangling_reference")
            if any(_id(r.note_id) in excluded for r in refs):
                issues.add("separator_reference")
            if any(not r.supported_context for r in refs):
                issues.add("unsupported_reference_context")
            tick()
            status = ExtractionStatus.NEEDS_REVIEW if notes or issues else ExtractionStatus.SUCCESS
            return AncillaryEvidence(
                status,
                digest,
                size,
                "/" + main,
                "/" + part,
                rid,
                tuple(notes),
                tuple(refs),
                tuple(sorted(issues)),
            )
    except _Failure as exc:
        return AncillaryEvidence(ExtractionStatus.FAILED, digest, size, issues=(str(exc),))
    except Exception:  # noqa: BLE001 - source/XML/library messages must never escape
        return AncillaryEvidence(ExtractionStatus.FAILED, digest, size, issues=("invalid_package",))
