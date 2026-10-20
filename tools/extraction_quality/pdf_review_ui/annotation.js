"use strict";
// Coordinates come only from this controlled raster, never the native PDF iframe.
const visual = {
  metadata: null, image: null, selection: null, history: [], drag: null,
  generation: 0, undoDraft: null,
  identity() {
    const page = item().draft.pages[number - 1];
    return {page_number: page.page_number, media_box_pdf_user_space: page.media_box_pdf_user_space,
      crop_box_pdf_user_space: page.crop_box_pdf_user_space, rotation: page.rotation};
  },
  pagePayload() { return {document_id: selected, page: number, page_identity: this.identity()}; },
  enabled() { return Boolean(this.metadata && this.image && !item().seal); },
  controls() {
    document.querySelectorAll("#visual-controls button,#visual-mode,#geometry-target").forEach(
      field => { field.disabled = !this.enabled(); });
    $("assign-geometry").disabled = !this.enabled() || !this.selection;
    $("undo-assignment").disabled = !this.enabled() || !this.undoDraft || this.undoDraft.document !== selected || this.undoDraft.revision !== state.revision;
    $("undo-selection").disabled = !this.enabled() || !this.history.length;
    grid.controls();
  },
  async load() {
    const generation = ++this.generation;
    this.metadata = this.image = this.selection = this.drag = null;
    this.history = []; this.controls(); this.paint();
    $("capture-status").textContent = "Rendering authorized original locally…";
    try {
      const meta = await api("render", this.pagePayload());
      if (generation !== this.generation) return;
      if (meta.document_id !== selected || meta.page !== number ||
          pretty(meta.page_identity) !== pretty(this.identity()) || meta.source_sha256 !== item().draft.source.sha256)
        throw new Error("Rendered page identity mismatch");
      const bytes = Uint8Array.from(atob(meta.png_base64), c => c.charCodeAt(0));
      const url = URL.createObjectURL(new Blob([bytes], {type: "image/png"}));
      const image = new Image();
      try { image.src = url; await image.decode(); } finally { URL.revokeObjectURL(url); }
      if (generation !== this.generation) return;
      if (image.naturalWidth !== meta.width || image.naturalHeight !== meta.height)
        throw new Error("Rendered image dimensions mismatch");
      this.metadata = meta; this.image = image;
      $("page-canvas").width = meta.width; $("page-canvas").height = meta.height;
      this.targets(); this.resize(); this.controls();
      $("capture-status").textContent = item().seal ? "Frozen draft: geometry is read-only." :
        `Local pypdfium2 ${meta.renderer} · ${meta.width} × ${meta.height} pixels · PDF-space capture enabled`;
    } catch (error) {
      if (generation !== this.generation) return;
      this.metadata = this.image = null; this.controls(); this.paint();
      $("capture-status").textContent = `Coordinate capture unavailable: ${error.message}. Use the original viewer for inspection.`;
    }
  },
  resize() {
    if (!this.metadata) return;
    this.drag = null;
    const width = $("visual-scroll").clientWidth * Number($("visual-zoom").value);
    $("page-canvas").style.width = `${width}px`;
    $("page-canvas").style.height = `${width * this.metadata.height / this.metadata.width}px`;
    this.paint();
  },
  point(event) {
    const rect = $("page-canvas").getBoundingClientRect();
    const point = [(event.clientX - rect.left) / rect.width, (event.clientY - rect.top) / rect.height];
    if (!point.every(v => Number.isFinite(v) && v >= 0 && v <= 1))
      throw new Error("Rectangle must remain inside the rendered original page");
    return point;
  },
  valid(rect) { return rect && rect.every(v => Number.isFinite(v) && v >= 0 && v <= 1) && rect[0] < rect[2] && rect[1] < rect[3]; },
  bbox() {
    if (!this.valid(this.selection)) throw new Error("Draw a non-zero rectangle inside the page");
    const [left, bottom, right, top] = this.metadata.page_identity.crop_box_pdf_user_space;
    const [x0, y0, x1, y1] = this.selection;
    return [left + x0 * (right - left), top - y1 * (top - bottom),
      left + x1 * (right - left), top - y0 * (top - bottom)];
  },
  paint() {
    const canvas = $("page-canvas"), context = canvas.getContext("2d");
    context.clearRect(0, 0, canvas.width, canvas.height);
    if (this.image) context.drawImage(this.image, 0, 0);
    grid.paint(context, canvas);
    if (this.valid(this.selection)) {
      const [x0, y0, x1, y1] = this.selection;
      context.fillStyle = "rgba(0,110,200,0.16)"; context.strokeStyle = "#0059ac"; context.lineWidth = 3;
      context.fillRect(x0 * canvas.width, y0 * canvas.height, (x1 - x0) * canvas.width, (y1 - y0) * canvas.height);
      context.strokeRect(x0 * canvas.width, y0 * canvas.height, (x1 - x0) * canvas.width, (y1 - y0) * canvas.height);
    }
    $("measured-bbox").textContent = this.metadata && this.valid(this.selection) ?
      `PDF bbox: [${this.bbox().map(v => v.toFixed(3)).join(", ")}]` : "No rectangle selected";
    this.controls();
  },
  targets() {
    const draft = gather(), previous = $("geometry-target").value, options = [];
    this.targetSnapshot = pretty({regions: read("regions"), tables: read("tables")});
    const add = (label, target) => {
      const option = document.createElement("option"); option.textContent = label; option.value = JSON.stringify(target); options.push(option);
    };
    draft.pages[number - 1].regions.forEach((r, region) => add(`Original region ${region + 1}: ${r.region_id || "ID required"}`, {kind: "region", region}));
    draft.tables.forEach((t, table) => {
      if (t.page_number !== number) return;
      add(`Table ${t.review_table_id || table + 1}`, {kind: "table", table});
      t.cells.forEach((c, cell) => {
        if ((c.page_number ?? number) === number)
          add(`Table ${t.review_table_id || table + 1} / cell ${c.review_cell_id || cell + 1}`, {kind: "cell", table, cell});
      });
    });
    $("geometry-target").replaceChildren(...options);
    if (options.some(o => o.value === previous)) $("geometry-target").value = previous;
  },
  target() {
    if (!$("geometry-target").value) throw new Error("Add a worksheet region/table/cell first");
    return JSON.parse($("geometry-target").value);
  },
  loadTarget() {
    const draft = gather(), target = this.target();
    let destination = target.kind === "region" ? draft.pages[number - 1].regions[target.region] : draft.tables[target.table];
    if (target.kind === "cell") destination = destination.cells[target.cell];
    const box = destination.bbox_pdf_user_space_points;
    if (!Array.isArray(box) || box.length !== 4 || !box.every(Number.isFinite)) throw new Error("Target has no measured rectangle");
    const [l, b, r, t] = this.metadata.page_identity.crop_box_pdf_user_space;
    const selection = [(box[0] - l) / (r - l), (t - box[3]) / (t - b), (box[2] - l) / (r - l), (t - box[1]) / (t - b)];
    if (!this.valid(selection)) throw new Error("Target rectangle is outside this page");
    this.history.push(this.selection); this.selection = selection; this.paint();
  },
  init() {
    const canvas = $("page-canvas");
    new ResizeObserver(() => this.resize()).observe($("visual-scroll"));
    $("visual-zoom").addEventListener("change", () => this.resize());
    canvas.addEventListener("pointerdown", event => {
      if (!this.enabled() || event.button !== 0) return;
      try {
        const start = this.point(event), mode = $("visual-mode").value;
        if (mode !== "draw" && !this.valid(this.selection)) throw new Error("Draw or load a rectangle first");
        this.drag = {start, before: this.selection && [...this.selection], mode};
        canvas.setPointerCapture(event.pointerId);
      } catch (error) { message(error.message, true); }
    });
    canvas.addEventListener("pointermove", event => {
      if (!this.drag) return;
      try {
        const point = this.point(event), {start, before, mode} = this.drag;
        if (mode === "draw") this.selection = [Math.min(start[0], point[0]), Math.min(start[1], point[1]), Math.max(start[0], point[0]), Math.max(start[1], point[1])];
        else if (mode === "resize") this.selection = [before[0], before[1], point[0], point[1]];
        else this.selection = before.map((v, i) => v + point[i % 2] - start[i % 2]);
        if (!this.valid(this.selection)) throw new Error("Rectangle must have area and remain inside the page");
        this.drag.valid = true; this.paint();
      } catch (error) { this.selection = this.drag.before; this.drag.valid = false; this.paint(); message(error.message, true); }
    });
    const finish = event => {
      if (!this.drag) return;
      if (event.type === "pointercancel" || !this.drag.valid) this.selection = this.drag.before;
      else this.history.push(this.drag.before);
      this.drag = null;
      if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
      this.paint();
    };
    canvas.addEventListener("pointerup", finish); canvas.addEventListener("pointercancel", finish);
    $("undo-selection").addEventListener("click", () => { this.selection = this.history.pop() || null; this.paint(); });
    $("cancel-selection").addEventListener("click", () => { this.history.push(this.selection); this.selection = null; this.paint(); });
    $("refresh-targets").addEventListener("click", safely(async () => this.targets()));
    $("load-target").addEventListener("click", safely(async () => this.loadTarget()));
    $("add-region").addEventListener("click", safely(async () => {
      const regions = read("regions"); regions.push({region_id: null, table_id: null, bbox_pdf_user_space_points: null});
      $("regions").value = pretty(regions); dirty = true; this.targets();
    }));
    $("add-cell").addEventListener("click", safely(async () => {
      const draft = gather(), target = this.target();
      if (target.kind === "region") throw new Error("Select a table or one of its cells first");
      draft.tables[target.table].cells.push(structuredClone(draft.cell_template));
      $("tables").value = pretty(draft.tables.filter(t => t.page_number === number)); dirty = true; this.targets();
    }));
    $("assign-geometry").addEventListener("click", safely(async () => {
      if (!this.enabled()) throw new Error("Geometry capture is disabled");
      if (this.targetSnapshot !== pretty({regions: read("regions"), tables: read("tables")}))
        throw new Error("Refresh targets from JSON before assigning changed worksheet targets");
      const previous = structuredClone(item().draft);
      message("Saving explicit geometry assignment…");
      state = await api("annotate", {...this.pagePayload(), render_id: this.metadata.render_id,
        bbox: this.bbox(), target: this.target(), draft: gather()});
      this.undoDraft = {document: selected, draft: previous, revision: state.revision};
      await render(); message("Rectangle explicitly assigned; worksheet saved locally. No semantic fields were inferred.");
    }));
    $("undo-assignment").addEventListener("click", safely(async () => {
      if (dirty) throw new Error("Save or reload edits before undoing an assignment");
      if (!this.undoDraft || this.undoDraft.document !== selected || this.undoDraft.revision !== state.revision)
        throw new Error("No current assignment to undo on this document");
      if (!confirm("Restore the worksheet saved before the last geometry assignment?")) return;
      message("Restoring the worksheet before geometry assignment…");
      state = await api("draft", {document_id: selected, draft: this.undoDraft.draft});
      this.undoDraft = null; await render(); message("Last geometry assignment undone locally.");
    }));
  }
};
