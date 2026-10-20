// All inputs are public synthetic fixtures. This exercises UI behavior, not human review.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {chromium} = require(path.join(process.env.ML30_NODE_MODULES, "playwright"));
(async () => {
  const cases = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
  const browser = await chromium.launch({channel: "msedge", headless: true, args: ["--disable-gpu"]});
  try {
    const page = await browser.newPage({viewport: {width: 1600, height: 1100}});
    const errors = []; page.on("pageerror", error => errors.push(error.message));
    await page.route("**/*", route => new URL(route.request().url()).origin === new URL(process.argv[2]).origin ? route.continue() : route.abort());
    await page.goto(process.argv[2], {waitUntil: "domcontentloaded"});
    await page.waitForFunction(() => document.querySelector("#capture-status").textContent.startsWith("Frozen draft"));
    for (const [index, proposal] of cases.proposals.entries()) {
      await page.locator("#proposal-file").setInputFiles({name: `synthetic-${index}.json`, mimeType: "application/json", buffer: Buffer.from(proposal)});
      page.once("dialog", dialog => dialog.accept());
      await page.locator("#import-proposal").click();
      await page.waitForFunction(count => document.querySelector("#proposal-cell").options.length === count, index + 1);
    }
    await page.locator("#validate").click();
    await page.waitForFunction(() => document.querySelector("#validation").textContent.includes('"export_ready": false'));
    await page.locator("#gold-revision").fill("public-synthetic-proposal-review-v1");
    page.once("dialog", dialog => dialog.accept());
    await page.locator("#export-gold").click();
    await page.waitForFunction(() => document.querySelector("#message").textContent.includes("no Gold exported"));
    const actions = ["confirm", "revise", "reject"];
    for (let index = 0; index < 3; index++) {
      await page.locator("#proposal-cell").selectOption(JSON.stringify([index, 0]));
      assert((await page.locator("#proposal-details").textContent()).includes('"page": 1'));
      await page.locator("#proposal-decision").selectOption(actions[index]);
      if (actions[index] !== "reject") await page.locator("#review-cell-ref").selectOption(JSON.stringify(cases.target, null, 2));
      await page.locator("#proposal-reviewer").fill("fixture-author");
      await page.locator("#proposal-date").fill("2026-01-02");
      await page.locator("#proposal-rationale").fill("Public synthetic oracle: inspect exact source locator");
      await page.locator("#proposal-evidence").fill(JSON.stringify(cases.evidence));
      await page.locator("#proposal-ambiguity").selectOption("false");
      if (index === 0) {
        page.once("dialog", dialog => dialog.dismiss());
        await page.locator("#proposal-cell").selectOption("[1,0]");
        assert.equal(await page.locator("#proposal-cell").inputValue(), "[0,0]");
      }
      await page.locator("#save-proposal-review").click();
      await page.waitForFunction(() => document.querySelector("#message").textContent.startsWith("Your proposal decision was saved"));
    }
    await page.reload({waitUntil: "domcontentloaded"});
    await page.waitForFunction(() => document.querySelector("#proposal-cell").options.length === 3);
    const labels = await page.locator("#proposal-cell option").allTextContents();
    assert(labels[0].includes("confirm") && labels[1].includes("revise") && labels[2].includes("reject"), JSON.stringify(labels));
    const canvasBox = await page.locator("#page-canvas").boundingBox();
    const worksheetBox = await page.locator("#comparison").boundingBox();
    assert(canvasBox && worksheetBox && canvasBox.x < worksheetBox.x, "original and proposed evidence must remain side by side");
    await page.locator("#gold-revision").fill("public-synthetic-proposal-review-v1");
    page.once("dialog", dialog => dialog.accept());
    await page.locator("#export-gold").click();
    await page.waitForFunction(() => document.querySelector("#message").textContent.startsWith("Exported "));
    assert.deepEqual(errors, []);
    console.log("Proposal review browser PASS: source visible, pending export blocked, confirm/correct/reject, unsaved-edit guard, resume and independent export");
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
