"use strict";
// Predictions are revealed only after the independent worksheet has been frozen.
const proposalReview = {
  dirty: false, selection: "",
  entries() { return item().adjudication?.proposal_reviews || []; },
  selected() {
    const value = $("proposal-cell").value;
    if (!value) return null;
    const [batch, index] = JSON.parse(value), entry = this.entries()[batch];
    if (!entry || !entry.proposal.cells[index]) return null;
    return {batch, index, entry, cell: entry.proposal.cells[index],
      decision: entry.decisions.find(d => d.proposal_cell_index === index)};
  },
  target() {
    if (!$("review-cell-ref").value) return null;
    const ref = JSON.parse($("review-cell-ref").value);
    const table = item().draft.tables.find(t => t.review_table_id === ref.table_id);
    return {ref, table, cell: table.cells.find(c => c.review_cell_id === ref.cell_id)};
  },
  refresh() {
    $("proposal-review").hidden = !state.exposed;
    if (!state.exposed) return;
    const previous = $("proposal-cell").value, options = [];
    this.entries().forEach((entry, batch) => entry.proposal.cells.forEach((cell, index) => {
      const option = document.createElement("option");
      option.value = JSON.stringify([batch, index]);
      option.textContent = `Proposal ${batch + 1}, cell ${index + 1}: row ${cell.row}, col ${cell.column} · ${entry.decisions.find(d => d.proposal_cell_index === index)?.decision || "UNREVIEWED"}`;
      options.push(option);
    }));
    $("proposal-cell").replaceChildren(...options);
    if (options.some(o => o.value === previous)) $("proposal-cell").value = previous;
    const blank = document.createElement("option"); blank.value = ""; blank.textContent = "Select independently recorded cell";
    const targets = [blank];
    item().draft.tables.forEach(table => table.cells.forEach(cell => {
      const option = document.createElement("option");
      option.value = pretty({table_id: table.review_table_id, cell_id: cell.review_cell_id});
      option.textContent = `${table.review_table_id} / ${cell.review_cell_id}: row ${cell.row}, col ${cell.column}, page ${cell.page_number ?? table.page_number} · ${cell.literal_text}`;
      targets.push(option);
    }));
    $("review-cell-ref").replaceChildren(...targets);
    this.show();
  },
  show() {
    this.dirty = false; this.selection = $("proposal-cell").value;
    const current = this.selected(), decision = current?.decision;
    $("save-proposal-review").disabled = !current;
    $("proposal-details").textContent = current ? pretty({
      proposal_sha256: current.entry.proposal_sha256,
      proposed_table_id: current.entry.proposal.context.review_table_id ?? null,
      proposed_table_index: current.entry.proposal.context.table_index,
      page: current.entry.proposal.context.page_identity.page_number,
      table_bbox: current.entry.proposal.context.bbox, proposed_cell: current.cell,
      original_machine_candidate: current.entry.proposal.candidate
    }) : "Import a saved proposal after completing the blind worksheet.";
    $("proposal-decision").value = decision?.decision || "";
    const ref = decision?.independent_cell_ref;
    $("review-cell-ref").value = ref ? pretty(ref) : "";
    $("proposal-reviewer").value = decision?.reviewer_id || "";
    $("proposal-date").value = decision?.reviewed_on || "";
    $("proposal-rationale").value = decision?.rationale || "";
    $("proposal-evidence").value = pretty(decision?.original_page_evidence || []);
    $("proposal-ambiguity").value = decision?.ambiguity === false ? "false" : decision?.ambiguity === true ? "true" : "";
    this.showTarget(); visual.paint();
  },
  showTarget() {
    const target = this.target();
    $("review-target-details").textContent = target ? pretty({
      table_id: target.table.review_table_id, page: target.cell.page_number ?? target.table.page_number,
      ...target.cell
    }) : "No independent cell selected. Rejections must have no target.";
  },
  paint(context, canvas) {
    const current = state?.exposed ? this.selected() : null;
    if (!current || !visual.metadata) return;
    const [left, bottom, right, top] = visual.metadata.page_identity.crop_box_pdf_user_space;
    const box = (bbox, page, color, label) => {
      if (page !== number) return;
      const [l, b, r, t] = bbox, x = (l - left) / (right - left) * canvas.width,
        y = (top - t) / (top - bottom) * canvas.height;
      context.strokeStyle = context.fillStyle = color; context.lineWidth = 3; context.font = "18px sans-serif";
      context.strokeRect(x, y, (r - l) / (right - left) * canvas.width, (t - b) / (top - bottom) * canvas.height);
      context.fillText(label, x + 3, y + 20);
    };
    context.save();
    box(current.cell.bbox_pdf_user_space_points, current.entry.proposal.context.page_identity.page_number, "#a436ad", "Proposed");
    const target = this.target();
    if (target) box(target.cell.bbox_pdf_user_space_points, target.cell.page_number ?? target.table.page_number, "#007b64", "Independent");
    context.restore();
  },
  init() {
    document.querySelectorAll("#proposal-review input:not(#proposal-file),#proposal-review textarea,#proposal-review select:not(#proposal-cell)").forEach(
      field => field.addEventListener("input", () => { this.dirty = true; }));
    window.addEventListener("beforeunload", event => { if (this.dirty) { event.preventDefault(); event.returnValue = ""; } });
    $("proposal-cell").addEventListener("change", () => {
      if (this.dirty && !confirm("Discard your unsaved proposal decision?")) {
        $("proposal-cell").value = this.selection; return;
      }
      this.show();
    });
    $("review-cell-ref").addEventListener("change", () => { this.showTarget(); visual.paint(); });
    $("import-proposal").addEventListener("click", safely(async () => {
      if (dirty || this.dirty) throw new Error("Save adjudication edits before importing");
      const file = $("proposal-file").files[0];
      if (!file || file.size > 20 * 1024 * 1024) throw new Error("Select one bounded saved proposal JSON file");
      if (!confirm("Reveal this proposal now? Your blind independent worksheet is already frozen. All proposal decisions start unreviewed.")) return;
      message("Importing proposal for separate review…");
      state = await api("proposal-import", {document_id: selected, proposal_json: await file.text(), confirm_import: true});
      await render(); message("Proposal imported for separate review; no decision or independent cell changed.");
    }));
    $("save-proposal-review").addEventListener("click", safely(async () => {
      if (dirty) throw new Error("Save other adjudication edits before recording a proposal decision");
      const current = this.selected();
      if (!current) throw new Error("Select a proposed cell");
      const adjudication = structuredClone(item().adjudication);
      const decision = adjudication.proposal_reviews[current.batch].decisions.find(d => d.proposal_cell_index === current.index);
      Object.assign(decision, {
        decision: $("proposal-decision").value || null,
        independent_cell_ref: this.target()?.ref || null,
        reviewer_id: $("proposal-reviewer").value || null,
        reviewed_on: $("proposal-date").value || null,
        rationale: $("proposal-rationale").value || null,
        original_page_evidence: read("proposal-evidence"),
        ambiguity: $("proposal-ambiguity").value === "" ? null : $("proposal-ambiguity").value === "true"
      });
      message("Saving your proposal decision…");
      state = await api("adjudication", {document_id: selected, adjudication});
      await render(); message("Your proposal decision was saved. Validate before export; missing or ambiguous decisions remain blocked.");
    }));
    $("export-gold").addEventListener("click", safely(async () => {
      if (dirty || this.dirty) throw new Error("Save adjudication before export");
      if (!confirm("Validate every review and export a new independent Gold revision locally? Rejected proposals are excluded; source Gold remains unchanged.")) return;
      const result = await api("export", {confirm_export: true, export_revision: $("gold-revision").value});
      $("validation").textContent = pretty(result);
      message(`Exported ${result.check_id}/reviewed-gold-v2.json under this workspace's checks directory. This validates supplied attestations; it does not perform human review.`);
    }));
  }
};
