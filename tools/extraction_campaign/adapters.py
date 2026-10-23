"""Candidate-specific native JSON adapters. Complete native JSON is retained separately."""

from __future__ import annotations

from html.parser import HTMLParser

from tools.extraction_campaign.evidence import Observation, unique


class NativeHTMLText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_endtag(self, tag):
        if tag in {"p", "div", "tr", "td", "th", "br", "li"}:
            self.parts.append("\n")


def docling_box(bbox):
    if bbox is None:
        return None, None
    origin = bbox.get("coord_origin")
    if origin == "TOPLEFT":
        return (bbox["l"], bbox["t"], bbox["r"], bbox["b"]), "top_left_points"
    if origin == "BOTTOMLEFT":
        return (bbox["l"], bbox["b"], bbox["r"], bbox["t"]), "bottom_left_points"
    return None, None


def docling(payload: dict) -> tuple[Observation, ...]:
    # Follow the explicit reference tree, including picture descendants and furniture.
    # Do not reorder the native arrays by guessed spatial proximity.
    out, visited, active = [], set(), set()

    def resolve(ref):
        if not isinstance(ref, dict) or set(ref) != {"$ref"}:
            raise ValueError("docling_reference")
        path = ref["$ref"].split("/")
        if (
            len(path) != 3
            or path[0] != "#"
            or path[1] not in {"texts", "tables", "pictures", "groups"}
            or not path[2].isdigit()
        ):
            raise ValueError("docling_reference")
        return payload[path[1]][int(path[2])]

    def walk(node, tree_parent=None):
        identity = node["self_ref"]
        if identity in active:
            raise ValueError("docling_cycle")
        if identity in visited:
            return
        active.add(identity)
        visited.add(identity)
        provs = node.get("prov", [])
        label = node.get("label", "group")
        text = node.get("text")
        if text is not None or label in {"table", "picture", "formula"}:
            if len(provs) > 1:
                # Native charspans must partition text; don't repeat whole text on each page.
                if text is not None and any("charspan" not in p for p in provs):
                    raise ValueError("docling_missing_charspan")
            for i, prov in enumerate(provs or [{}]):
                coords, basis = docling_box(prov.get("bbox"))
                value = text
                if text is not None and len(provs) > 1:
                    start, end = prov["charspan"]
                    if (
                        type(start) is not int
                        or type(end) is not int
                        or not 0 <= start <= end <= len(text)
                    ):
                        raise ValueError("docling_charspan")
                    value = text[start:end]
                out.append(
                    Observation(
                        native_id=f"{identity}/prov/{i}",
                        kind=label,
                        text=value,
                        page=prov.get("page_no"),
                        order=len(out),
                        bbox=coords,
                        coordinate_system=basis,
                        parent=node.get("parent", {}).get("$ref", tree_parent),
                        unresolved=(() if prov else ("missing_provenance",)),
                    )
                )
            if label == "table":
                # Cells carry native logical spans. A table's first provenance is not
                # sufficient to assign every cell of a multipage table to that page.
                table_page = provs[0].get("page_no") if len(provs) == 1 else None
                for i, cell in enumerate(node.get("data", {}).get("table_cells", [])):
                    cell_box, cell_basis = docling_box(cell.get("bbox"))
                    start_r, end_r = (
                        cell.get("start_row_offset_idx"),
                        cell.get("end_row_offset_idx"),
                    )
                    start_c, end_c = (
                        cell.get("start_col_offset_idx"),
                        cell.get("end_col_offset_idx"),
                    )
                    out.append(
                        Observation(
                            native_id=f"{identity}/cell/{i}",
                            kind="cell",
                            text=cell.get("text"),
                            page=table_page,
                            order=len(out),
                            table=identity,
                            row=start_r,
                            column=start_c,
                            row_span=end_r - start_r
                            if start_r is not None and end_r is not None
                            else None,
                            column_span=end_c - start_c
                            if start_c is not None and end_c is not None
                            else None,
                            parent=identity,
                            bbox=cell_box,
                            coordinate_system=cell_basis,
                            unresolved=("cell_page_ownership_unknown",)
                            if table_page is None
                            else ()
                            if cell_box is not None
                            else ("cell_geometry_unknown",),
                        )
                    )
        for child in node.get("children", []):
            walk(resolve(child), identity)
        active.remove(identity)

    for root in ("body", "furniture"):
        if root in payload:
            walk(payload[root])
    return unique(out)


def paddle(payload: dict) -> tuple[Observation, ...]:
    """PaddleX JSON wrapper contains explicit zero-based page_index and parsing_res_list."""
    data = payload.get("res", payload)
    page_index = data.get("page_index")
    if page_index is not None and (type(page_index) is not int or page_index < 0):
        raise ValueError("paddle_page")
    page = page_index + 1 if page_index is not None else None
    out = []
    for i, block in enumerate(data.get("parsing_res_list", [])):
        box = block.get("block_bbox")
        content = block.get("block_content")
        if block.get("block_label") == "table" and content is not None:
            projection = NativeHTMLText()
            projection.feed(content)
            content = "".join(projection.parts)
        out.append(
            Observation(
                native_id=f"page/{page}/block/{block.get('block_id', i)}",
                kind=block.get("block_label", "unknown"),
                text=content,
                page=page,
                order=i,
                bbox=tuple(box) if box is not None else None,
                coordinate_system="top_left_pixels" if box is not None else None,
                unresolved=("table_html_retained_native_not_cell_gold",)
                if block.get("block_label") == "table"
                else (),
            )
        )
    # Do not flatten table OCR, cell_box_list, pred_html into invented associations.
    # All remain fully represented in the native output sidecar.
    return unique(out)


def mineru(payload: dict) -> tuple[Observation, ...]:
    """MinerU middle.json contains explicit page_info/page_idx and paragraph blocks."""
    out = []
    for page in payload.get("pdf_info", []):
        index = page.get("page_idx")
        if index is not None and (type(index) is not int or index < 0):
            raise ValueError("mineru_page")
        number = index + 1 if index is not None else None
        for i, block in enumerate(page.get("para_blocks", [])):
            texts = []
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("content") is not None:
                        texts.append(span["content"])
            # Explicit line/span order supplies separators; original native content survives.
            box = block.get("bbox")
            out.append(
                Observation(
                    native_id=f"page/{number}/block/{i}",
                    kind=block.get("type", "unknown"),
                    text="\n".join(texts) if texts else None,
                    page=number,
                    order=len(out),
                    bbox=tuple(box) if box is not None else None,
                    coordinate_system=None,  # Must be verified for the exact installed workflow.
                    unresolved=("coordinate_basis_requires_native_schema_verification",),
                )
            )
    return unique(out)


def marker(payload: dict) -> tuple[Observation, ...]:
    # Marker JSONRenderer: explicit tree of blocks, page IDs and html. HTML is
    # retained as native structure; plain-text decoding is a separate projection.
    out = []

    def walk(node, page=None, parent=None):
        identity = node.get("id")
        if not isinstance(identity, str):
            raise ValueError("marker_identity")
        kind = node.get("block_type", "unknown")
        match = __import__("re").fullmatch(r"/page/(\d+)(?:/.*)?", identity)
        if match:
            page = int(match[1]) + 1
        parser = NativeHTMLText()
        if node.get("html") is not None:
            parser.feed(node["html"])
        text = "".join(parser.parts) if node.get("html") is not None else None
        box = node.get("bbox")
        out.append(
            Observation(
                native_id=identity,
                kind=kind,
                text=text,
                page=page,
                order=len(out),
                bbox=tuple(box) if box is not None else None,
                coordinate_system=None,
                parent=parent,
                unresolved=("native_coordinate_basis_not_assumed",),
            )
        )
        for child in node.get("children") or []:
            walk(child, page, identity)

    for child in payload.get("children", []):
        walk(child)
    return unique(out)
