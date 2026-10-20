"use strict";
// Vanilla local UI. Never interpolate worksheet/source text into HTML.
const $ = id => document.getElementById(id);
const token = location.pathname.split("/")[1];
let state, selected, number = 1, dirty = false;
const pretty = value => JSON.stringify(value, null, 2);
const item = () => state.documents[selected];
function message(text, error = false) {
  $("message").textContent = text;
  $("message").classList.toggle("error", error);
}
async function api(path, payload) {
  const options = payload === undefined ? {} : {method: "POST",
    headers: {"Content-Type": "application/json", "X-Review-Token": token},
    body: JSON.stringify({...payload, revision: state.revision})};
  const response = await fetch(path, {...options, cache: "no-store", credentials: "omit"});
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || "Local request blocked");
  return value;
}
function safely(action) {
  return async () => { try { await action(); } catch (error) { message(error.message, true); } };
}
function mayNavigate() { return (!dirty && !grid.dirty && !proposalReview.dirty) || confirm("Discard unsaved worksheet/proposal edits and load the saved worksheet?"); }
function read(id) { return JSON.parse($(id).value); }
function gather() {
  const draft = structuredClone(item().draft);
  const page = draft.pages[number - 1];
  page.table_presence = read("presence"); page.regions = read("regions");
  page.notes = $("notes").value || null;
  const tables = read("tables"), anchors = read("anchors");
  if (!Array.isArray(tables) || tables.some(t => t.page_number !== number))
    throw new Error("Page tables must be an array with the selected page_number");
  if (!Array.isArray(anchors) || anchors.some(a => a.locator.page !== number))
    throw new Error("Page anchors must use the selected locator.page");
  draft.tables = [...draft.tables.filter(t => t.page_number !== number), ...tables];
  draft.text_anchors = [...draft.text_anchors.filter(a => a.locator.page !== number), ...anchors];
  draft.order_pairs = read("order"); draft.reviewer = read("reviewer");
  draft.family_language = read("family"); draft.completion = read("completion");
  return draft;
}
async function render() {
  const current = item(), draft = current.draft, page = draft.pages[number - 1];
  $("document").value = selected;
  $("page-label").textContent = `Page ${number} of ${draft.pages.length}`;
  $("previous").disabled = number === 1; $("next").disabled = number === draft.pages.length;
  const url = `original.pdf?document_id=${encodeURIComponent(selected)}#page=${number}`;
  if ($("pdf").getAttribute("src") !== url) $("pdf").src = url;
  $("open-pdf").href = url;
  $("geometry").textContent = `MediaBox ${pretty(page.media_box_pdf_user_space)} · ` +
    `CropBox ${pretty(page.crop_box_pdf_user_space)} · rotation ${page.rotation}°`;
  $("inspected").checked = current.inspected_pages.includes(number);
  $("inspected").disabled = Boolean(current.seal);
  $("phase").textContent = current.seal ? "· frozen" : "· in progress";
  $("seal").textContent = current.seal ? `Independent fingerprint: ${current.seal}` : "Not fingerprinted";
  $("presence").value = JSON.stringify(page.table_presence);
  $("regions").value = pretty(page.regions); $("notes").value = page.notes || "";
  $("tables").value = pretty(draft.tables.filter(t => t.page_number === number));
  $("anchors").value = pretty(draft.text_anchors.filter(a => a.locator.page === number));
  $("order").value = pretty(draft.order_pairs); $("reviewer").value = pretty(draft.reviewer);
  $("family").value = pretty(draft.family_language); $("completion").value = pretty(draft.completion);
  $("templates").textContent = pretty({cell: draft.cell_template, relationship: draft.relationship_template});
  $("independent-fields").querySelectorAll("textarea,select,button").forEach(
    field => { field.disabled = Boolean(current.seal); });
  $("reveal").disabled = state.exposed || !Object.values(state.documents).every(d => d.seal);
  $("comparison").hidden = !state.exposed;
  if (state.exposed) {
    $("legacy").textContent = pretty(await api(`legacy?document_id=${encodeURIComponent(selected)}`));
    $("adjudication").value = pretty(current.adjudication);
  }
  dirty = false;
  grid.clear();
  proposalReview.refresh();
  await visual.load();
}
async function load() {
  state = await api("state");
  const keys = Object.keys(state.documents);
  if (!selected || !keys.includes(selected)) selected = keys[0];
  $("document").replaceChildren(...keys.map(key => {
    const option = document.createElement("option"); option.value = key; option.textContent = key;
    return option;
  }));
  number = Math.min(number, item().draft.pages.length);
  await render(); message("Saved local worksheet loaded. Human decisions are never filled automatically.");
}
$("document").addEventListener("change", safely(async () => {
  if (!mayNavigate()) { $("document").value = selected; return; }
  selected = $("document").value; number = 1; await render();
}));
for (const [id, delta] of [["previous", -1], ["next", 1]]) $(id).addEventListener("click", safely(async () => {
  if (mayNavigate()) { number += delta; await render(); }
}));
$("reload").addEventListener("click", safely(async () => { if (mayNavigate()) await load(); }));
$("save").addEventListener("click", safely(async () => {
  state = await api("draft", {document_id: selected, draft: gather()});
  await render(); message("Independent draft saved locally.");
}));
$("inspected").addEventListener("change", safely(async () => {
  if (dirty) { $("inspected").checked = item().inspected_pages.includes(number);
    throw new Error("Save or reload your edits before recording page inspection"); }
  state = await api("inspect", {document_id: selected, page: number, inspected: $("inspected").checked});
  message("Your page-inspection choice was saved locally.");
}));
$("freeze").addEventListener("click", safely(async () => {
  if (dirty) throw new Error("Save the independent draft before freezing");
  if (!confirm("Freeze your completed independent review? All attestations must be your own. This snapshot cannot be edited here.")) return;
  state = await api("freeze", {document_id: selected, confirm_freeze: true});
  await render(); message("Independent draft fingerprinted. Other selected PDFs must also be completed before legacy comparison.");
}));
$("reveal").addEventListener("click", safely(async () => {
  if (!confirm("Reveal legacy assertions now that every independent draft is frozen? This permanently ends blind review in this workbench.")) return;
  state = await api("reveal", {confirm_reveal: true}); await render();
  message("Legacy comparison unlocked. Every adjudication decision remains yours to enter.");
}));
$("add-table").addEventListener("click", safely(async () => {
  const values = read("tables"), table = structuredClone(item().draft.table_template);
  table.page_number = number; table.coordinate_basis = "pdf_user_space_unrotated";
  values.push(table); $("tables").value = pretty(values); dirty = true;
}));
$("add-anchor").addEventListener("click", safely(async () => {
  const values = read("anchors"); values.push({anchor_id: null, literal: null,
    locator: {page: number, bbox: null, coordinate_basis: "pdf_user_space_unrotated"},
    occurrence: null, category: null});
  $("anchors").value = pretty(values); dirty = true;
}));
$("save-adjudication").addEventListener("click", safely(async () => {
  if (proposalReview.dirty) throw new Error("Save your proposal decision before other adjudication edits");
  state = await api("adjudication", {document_id: selected, adjudication: read("adjudication")});
  await render(); message("Human adjudication draft saved locally.");
}));
$("validate").addEventListener("click", safely(async () => {
  if (dirty || proposalReview.dirty) throw new Error("Save adjudication before validation");
  const result = await api("validate", {});
  $("validation").textContent = pretty(result);
  message(result.summary.export_ready ? "Existing ML-28 validation accepted the supplied review. No Gold was exported." :
    "Existing ML-28 validation remains blocked. Review the pending decisions.");
}));
document.querySelectorAll("textarea:not(#grid-cells),#presence").forEach(field => field.addEventListener("input", () => {
  if (!field.closest("#proposal-review")) dirty = true;
}));
window.addEventListener("beforeunload", event => { if (dirty) { event.preventDefault(); event.returnValue = ""; } });
visual.init();
grid.init();
proposalReview.init();
load().catch(error => message(error.message, true));
