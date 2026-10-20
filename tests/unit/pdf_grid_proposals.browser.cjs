// Actual overlay/correction/acceptance path against public synthetic originals only.
const assert = require("node:assert/strict");
const path = require("node:path");
const {chromium} = require(path.join(process.env.ML30_NODE_MODULES, "playwright"));
(async () => {
  const browser = await chromium.launch({channel: "msedge", headless: true, args: ["--disable-gpu"]});
  try {
    const page = await browser.newPage({viewport: {width: 1400, height: 1000}});
    const errors = []; page.on("pageerror", error => errors.push(error.message));
    await page.route("**/*", route => new URL(route.request().url()).origin === new URL(process.argv[2]).origin ? route.continue() : route.abort());
    await page.goto(process.argv[2], {waitUntil: "domcontentloaded"});
    const ready = () => page.waitForFunction(() => document.querySelector("#capture-status").textContent.includes("capture enabled"));
    await ready();
    page.once("dialog", dialog => dialog.accept());
    await page.locator("#grid-propose").click();
    await page.waitForFunction(() => document.querySelector("#grid-status").textContent.startsWith("PROPOSED: 6"));
    assert.equal(JSON.parse(await page.locator("#tables").inputValue())[0].cells.length, 0);
    const overlayPixels = () => page.locator("#page-canvas").evaluate(canvas => {
      const data = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height).data;
      let count = 0;
      for (let i = 0; i < data.length; i += 4) if (data[i] > 100 && data[i + 1] < 100 && data[i + 2] > 100) count++;
      return count;
    });
    assert(await overlayPixels() > 100, "actual proposed grid overlay must be painted");
    await page.locator("#visual-zoom").selectOption("2");
    assert(await overlayPixels() > 100);
    const cells = JSON.parse(await page.locator("#grid-cells").inputValue());
    cells[0].literal_text = "Explicit corrected public text";
    cells[0].bbox_pdf_user_space_points[2] -= 0.2;
    await page.locator("#grid-cells").fill(JSON.stringify(cells));
    await page.locator("#grid-correct").click();
    await page.waitForFunction(() => document.querySelector("#message").textContent.includes("corrections saved separately"));
    await page.reload({waitUntil: "domcontentloaded"}); await ready();
    await page.locator("#grid-load").click();
    await page.waitForFunction(() => document.querySelector("#grid-status").textContent.startsWith("PROPOSED: 6"));
    assert.equal(JSON.parse(await page.locator("#grid-cells").inputValue())[0].literal_text, "Explicit corrected public text");
    page.once("dialog", dialog => dialog.dismiss());
    await page.locator("#grid-accept").click();
    assert.equal(JSON.parse(await page.locator("#tables").inputValue())[0].cells.length, 0);
    page.once("dialog", dialog => dialog.accept());
    await page.locator("#grid-accept").click();
    await page.waitForFunction(() => document.querySelector("#message").textContent.startsWith("Accepted 6 draft cell proposals"));
    await page.reload({waitUntil: "domcontentloaded"}); await ready();
    const table = JSON.parse(await page.locator("#tables").inputValue())[0];
    assert.equal(table.cells.length, 6);
    assert.equal(table.cells[0].literal_text, "Explicit corrected public text");
    assert(table.cells.every(c => c.uncertain === null && c.evidence_reference === null && c.proposal_origin));
    assert.equal(table.structure_complete, null);
    assert(Object.values(JSON.parse(await page.locator("#reviewer").inputValue())).every(v => v === null));
    assert(await page.locator("#reveal").isDisabled());
    assert.deepEqual(errors, []);
    console.log("Grid browser PASS: actual overlay, zoom, correction, reload/resume, cancel/explicit acceptance, null attestations, locked legacy");
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
