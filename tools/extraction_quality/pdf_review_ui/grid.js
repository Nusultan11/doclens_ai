"use strict";
// Machine proposals have their own ignored sidecar and never supply review attestations.
const grid = {
  record: null, dirty: false,
  clear() {
    this.record = null; this.dirty = false;
    $("grid-cells").value = ""; $("grid-details").textContent = "";
    $("grid-status").textContent = "No assisted proposal loaded";
    this.controls();
  },
  controls() {
    const enabled = visual.enabled();
    for (const id of ["grid-propose", "grid-load"]) $(id).disabled = !enabled;
    for (const id of ["grid-correct", "grid-accept"])
      $(id).disabled = !enabled || !this.record || !this.record.applicable || this.record.candidate.status !== "PROPOSED";
    $("grid-clear").disabled = !this.record;
    $("grid-cells").disabled = !enabled || !this.record || !this.record.applicable || this.record.candidate.status !== "PROPOSED";
  },
  payload() {
    if (dirty) throw new Error("Save the worksheet before working with proposals");
    const target = visual.target();
    if (target.kind === "region") throw new Error("Select a saved table or one of its cells");
    if (this.record && this.record.context.table_index !== target.table)
      throw new Error("Hide the previous proposal before selecting another table");
    return {...visual.pagePayload(), table_index: target.table};
  },
  show(record) {
    this.record = record; this.dirty = false;
    $("grid-cells").value = pretty(record.cells);
    $("grid-details").textContent = pretty({proposal_id: record.proposal_id, context: record.context,
      method: record.candidate.method, issues: record.candidate.issues,
      detected: record.candidate.detected_internal_dividers,
      x_boundaries: record.candidate.x_boundaries, y_boundaries: record.candidate.y_boundaries});
    $("grid-status").textContent = `${record.candidate.status}: ${record.cells.length} proposed cells. ` +
      (record.applicable ? "Inspect every boundary and literal. Existing cells will be preserved." : "Stale proposal: worksheet changed; acceptance is blocked.");
    visual.paint();
  },
  paint(context, canvas) {
    if (!this.record || !visual.metadata || this.record.context.document_id !== selected ||
        this.record.context.page_identity.page_number !== number) return;
    const [left, bottom, right, top] = visual.metadata.page_identity.crop_box_pdf_user_space;
    context.save(); context.strokeStyle = "#a436ad"; context.fillStyle = "#7d1b85";
    context.lineWidth = 2; context.font = "18px sans-serif";
    for (const cell of this.record.cells) {
      const [l, b, r, t] = cell.bbox_pdf_user_space_points;
      const x = (l - left) / (right - left) * canvas.width;
      const y = (top - t) / (top - bottom) * canvas.height;
      context.strokeRect(x, y, (r - l) / (right - left) * canvas.width, (t - b) / (top - bottom) * canvas.height);
      context.fillText(`${cell.row},${cell.column}`, x + 3, y + 20);
    }
    context.restore();
  },
  init() {
    $("grid-cells").addEventListener("input", () => { this.dirty = true; });
    window.addEventListener("beforeunload", event => { if (this.dirty) { event.preventDefault(); event.returnValue = ""; } });
    $("grid-clear").addEventListener("click", () => {
      if (!this.dirty || confirm("Discard unsaved proposal corrections?")) { this.clear(); visual.paint(); }
    });
    for (const action of ["propose", "load"]) $("grid-" + action).addEventListener("click", safely(async () => {
      if (this.dirty) throw new Error("Save proposal corrections before reloading");
      const payload = this.payload();
      if (action === "propose" && !confirm("Generate machine-assisted grid/text proposals from this original? This document will require separate independent review before Gold freeze.")) return;
      message("Loading original-only grid proposal…");
      this.show(await api("grid-" + action, payload));
      message("Machine proposal loaded separately; no worksheet cells or review attestations changed.");
    }));
    $("grid-correct").addEventListener("click", safely(async () => {
      const payload = this.payload();
      message("Saving proposal corrections…");
      this.show(await api("grid-correct", {...payload, proposal_revision: this.record.proposal_revision,
        cells: read("grid-cells")}));
      message("Proposal corrections saved separately; overlay redrawn.");
    }));
    $("grid-accept").addEventListener("click", safely(async () => {
      const payload = this.payload();
      if (this.dirty) throw new Error("Save proposal corrections before acceptance");
      if (!confirm("Accept missing proposed cells into this draft? Existing cells stay unchanged. No uncertainty, evidence, completeness or reviewer approval will be set.")) return;
      message("Saving explicitly accepted proposal cells…");
      const result = await api("grid-accept", {...payload, proposal_revision: this.record.proposal_revision, confirm_accept: true});
      state = result.state; await render();
      message(`Accepted ${result.added} draft cell proposals; preserved ${result.preserved} existing cells. Separate independent review is still required for Gold.`);
    }));
  }
};
