"""Literal OOXML observations, independent of DocLens predictions and human Gold.

No formulas, external relationships or rendering engines are executed. XML paths
refer to physical package elements, never inferred Word pages or display values.
"""

from __future__ import annotations

import posixpath
import re
import stat
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

from openpyxl.styles.numbers import BUILTIN_FORMATS

from doclens_ai.eda import corpus_v2 as corpus

VERSION = "office-source-oracle-1.1"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class Package:
    def __init__(self, path: Path):
        corpus.no_links(path)
        self.archive = zipfile.ZipFile(path)
        infos = self.archive.infolist()
        names = [i.filename for i in infos]
        if len(names) > 20_000 or len(names) != len(set(names)):
            self.archive.close()
            raise ValueError("duplicate or excessive ZIP members")
        total = 0
        for info in infos:
            p = PurePosixPath(info.filename)
            total += info.file_size
            if (
                p.is_absolute()
                or ".." in p.parts
                or "\\" in info.filename
                or ":" in info.filename
                or stat.S_ISLNK(info.external_attr >> 16)
                or info.flag_bits & 1
                or info.file_size > 64 * 1024**2
                or info.file_size / max(info.compress_size, 1) > 200
                or total > 256 * 1024**2
            ):
                self.archive.close()
                raise ValueError("unsafe or over-budget ZIP")
        self.names = set(names)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.archive.close()

    def xml(self, part: str) -> ET.Element:
        raw = self.archive.read(part)
        if b"\x00" in raw or re.search(rb"<!\s*(DOCTYPE|ENTITY)", raw, re.I):
            raise ValueError("DTD/entities rejected")
        return ET.fromstring(raw)

    def relationships(self, part: str) -> dict[str, dict]:
        name = posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")
        if name not in self.names:
            return {}
        result = {}
        for node in self.xml(name):
            key, target = node.attrib["Id"], node.attrib["Target"]
            if key in result:
                raise ValueError("duplicate relationship ID")
            external = node.get("TargetMode") == "External"
            resolved = None
            if not external:
                resolved = posixpath.normpath(
                    target.lstrip("/")
                    if target.startswith("/")
                    else posixpath.join(posixpath.dirname(part), target)
                )
                if (
                    resolved.startswith("../")
                    or "\\" in resolved
                    or ":" in resolved
                    or resolved not in self.names
                ):
                    raise ValueError("invalid internal relationship")
            result[key] = {
                "type": node.attrib["Type"],
                "target": target,
                "part": resolved,
                "external": external,
            }
        return result


def docx(pkg: Package) -> dict:
    main = "word/document.xml"
    if pkg.xml(main).tag != f"{{{W}}}document":
        raise ValueError("DOCX main root mismatch")
    parts, visited, queue = {}, set(), [(main, "document")]
    supported = {
        "header": "hdr",
        "footer": "ftr",
        "footnotes": "footnotes",
        "endnotes": "endnotes",
        "comments": "comments",
    }
    while queue:
        part, expected_root = queue.pop(0)
        root = pkg.xml(part)
        if root.tag != f"{{{W}}}{expected_root}":
            raise ValueError("DOCX relationship/root mismatch")
        if part in visited:
            continue
        visited.add(part)
        relationships = pkg.relationships(part)
        queue.extend(
            (r["part"], supported[r["type"].rsplit("/", 1)[-1]])
            for r in relationships.values()
            if not r["external"] and r["type"].rsplit("/", 1)[-1] in supported
        )
        records = []
        uris = sorted(
            {
                n.tag[1:].split("}", 1)[0]
                for n in root.iter()
                if n.tag.startswith("{") and not n.tag.startswith("{" + W + "}")
            }
        )
        namespaces = {"w": W, **{f"n{i}": uri for i, uri in enumerate(uris)}}
        prefixes = {uri: prefix for prefix, uri in namespaces.items()}

        def qualified(tag, prefixes=prefixes):
            if tag.startswith("{"):
                uri, name = tag[1:].split("}", 1)
                return prefixes[uri] + ":" + name
            return tag

        def walk(
            node, address, part=part, records=records, namespaces=namespaces, qualified=qualified
        ):
            if address.count("/") > 128:
                raise ValueError("XML nesting bound")
            name = local(node.tag)
            if node.tag.startswith("{" + W + "}") and name in {
                "p",
                "tbl",
                "tr",
                "tc",
                "sectPr",
                "footnote",
                "endnote",
                "comment",
                "footnoteReference",
                "endnoteReference",
                "headerReference",
                "footerReference",
                "gridSpan",
                "vMerge",
                "hMerge",
                "pStyle",
                "outlineLvl",
                "tblGrid",
                "gridCol",
            }:
                record = {
                    "locator": {"part": part, "xml_path": address, "namespaces": namespaces.copy()},
                    "kind": name,
                    "attributes": dict(node.attrib),
                }
                if name == "p":
                    record["tokens"] = [
                        {"tag": local(n.tag), "text": n.text, "attributes": dict(n.attrib)}
                        for n in node.iter()
                        if local(n.tag)
                        in {
                            "t",
                            "delText",
                            "instrText",
                            "tab",
                            "br",
                            "cr",
                            "sym",
                            "footnoteReference",
                            "endnoteReference",
                            "fldChar",
                        }
                    ]
                    record["native_t_text"] = "".join(n.text or "" for n in node.iter(f"{{{W}}}t"))
                records.append(record)
            counts = Counter()
            for child in node:
                counts[child.tag] += 1
                walk(child, address + "/" + qualified(child.tag) + f"[{counts[child.tag]}]")

        walk(root, "/" + qualified(root.tag) + "[1]")
        parts[part] = {"relationships": relationships, "elements": records}
    return {
        "parts": parts,
        "order_scope": "physical XML order within each part",
        "page_numbers": None,
        "display_text": None,
        "unsupported": [
            "layout",
            "tracked_change_visibility",
            "drawing_text",
            "styles_inheritance",
        ],
    }


def xlsx(pkg: Package) -> dict:
    part = "xl/workbook.xml"
    root = pkg.xml(part)
    if root.tag != f"{{{S}}}workbook":
        raise ValueError("XLSX main root mismatch")
    relationships = pkg.relationships(part)
    shared, formats, styles = [], {}, []
    for rel in relationships.values():
        if rel["external"]:
            continue
        if rel["type"].endswith("/sharedStrings"):
            shared = [
                "".join(t.text or "" for t in si.iter(f"{{{S}}}t")) for si in pkg.xml(rel["part"])
            ]
        if rel["type"].endswith("/styles"):
            style_root = pkg.xml(rel["part"])
            formats = {
                int(n.attrib["numFmtId"]): n.attrib["formatCode"]
                for n in style_root.findall(f"{{{S}}}numFmts/{{{S}}}numFmt")
            }
            styles = [dict(n.attrib) for n in style_root.findall(f"{{{S}}}cellXfs/{{{S}}}xf")]
    sheets = []
    for sheet in root.findall(f"{{{S}}}sheets/{{{S}}}sheet"):
        rid = sheet.attrib[f"{{{R}}}id"]
        rel = relationships[rid]
        if rel["external"] or not rel["type"].endswith("/worksheet"):
            sheets.append(
                {
                    "sheet": dict(sheet.attrib),
                    "relationship": rel,
                    "state": "UNSUPPORTED_SHEET_KIND",
                }
            )
            continue
        worksheet = pkg.xml(rel["part"])
        if worksheet.tag != f"{{{S}}}worksheet":
            raise ValueError("worksheet root mismatch")
        cells, seen = [], set()
        for node in worksheet.findall(f"{{{S}}}sheetData/{{{S}}}row/{{{S}}}c"):
            address = node.attrib["r"]
            if not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]{0,6}", address) or address in seen:
                raise ValueError("duplicate or malformed stored cell address")
            seen.add(address)
            letters = re.match(r"[A-Z]+", address)[0]
            column = 0
            for letter in letters:
                column = column * 26 + ord(letter) - ord("A") + 1
            if column > 16384 or int(address[len(letters) :]) > 1048576:
                raise ValueError("cell outside worksheet bounds")
            if any(len(node.findall(f"{{{S}}}{tag}")) > 1 for tag in ("v", "f", "is")):
                raise ValueError("duplicate cell value/formula")
            value, formula = node.find(f"{{{S}}}v"), node.find(f"{{{S}}}f")
            inline = node.find(f"{{{S}}}is")
            stored_type = node.get("t", "n")
            lexical = None if value is None else (value.text or "")
            resolved = None
            if stored_type == "s":
                if lexical is None or not lexical.isdigit() or int(lexical) >= len(shared):
                    raise ValueError("shared string index rejected")
                resolved = shared[int(lexical)]
            elif inline is not None:
                resolved = "".join(n.text or "" for n in inline.iter(f"{{{S}}}t"))
            style_index = int(node.get("s", "0"))
            if style_index < 0 or (style_index >= len(styles) if styles else style_index != 0):
                raise ValueError("style index rejected")
            style = styles[style_index] if styles else {}
            fmt_id = int(style.get("numFmtId", "0"))
            cells.append(
                {
                    "locator": {
                        "part": rel["part"],
                        "sheet_id": sheet.get("sheetId"),
                        "sheet_name": sheet.get("name"),
                        "cell": address,
                    },
                    "stored_type": stored_type,
                    "stored_v_present": value is not None,
                    "stored_v": lexical,
                    "resolved_string": resolved,
                    "formula": None
                    if formula is None
                    else {"text": formula.text, "attributes": dict(formula.attrib)},
                    "cache_state": "NOT_FORMULA"
                    if formula is None
                    else ("MISSING" if value is None else "EMPTY" if lexical == "" else "PRESENT"),
                    "style_index": style_index,
                    "num_format_id": fmt_id,
                    "num_format": formats.get(fmt_id, BUILTIN_FORMATS.get(fmt_id)),
                    "date_interpretation": "ISO_STORED"
                    if stored_type == "d"
                    else "NOT_INTERPRETED",
                    "display_value": None,
                }
            )
        sheets.append(
            {
                "sheet": dict(sheet.attrib),
                "relationship": rel,
                "cells": cells,
                "missing_cell_semantics": "absent physical c element; not a stored blank",
                "merges": [
                    n.attrib["ref"]
                    for n in worksheet.findall(f"{{{S}}}mergeCells/{{{S}}}mergeCell")
                ],
                "relationships": pkg.relationships(rel["part"]),
            }
        )
    properties = root.find(f"{{{S}}}workbookPr")
    return {
        "sheets": sheets,
        "date1904": None if properties is None else properties.get("date1904"),
        "relationships": relationships,
        "calculated": False,
        "display_verified": False,
    }


def observe(path: Path, source_id: str, sha256: str, fmt: str) -> dict:
    corpus.no_links(path)
    if fmt not in {"docx", "xlsx"} or corpus.sha256(path) != sha256:
        raise ValueError("oracle source identity rejected")
    with Package(path) as package:
        observations = docx(package) if fmt == "docx" else xlsx(package)
    if corpus.sha256(path) != sha256:
        raise ValueError("source changed during observation")
    return {
        "version": VERSION,
        "source_id": source_id,
        "source_sha256": sha256,
        "format": fmt,
        "tier": "SOURCE_NATIVE_ORACLE",
        "human_reviewed": False,
        "reviewer": None,
        "independent_gold": False,
        "observations": observations,
    }
