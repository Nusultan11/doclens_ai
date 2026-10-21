// Public synthetic files only; all network requests are rejected.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {pathToFileURL} = require("node:url");
const {chromium} = require(path.join(process.env.ML30_NODE_MODULES, "playwright"));

(async () => {
  const root = path.resolve(process.argv[2]);
  const counts = JSON.parse(fs.readFileSync(path.join(root, "counts.json"), "utf8"));
  const browser = await chromium.launch({channel: "msedge", headless: true, args: ["--disable-gpu"]});
  try {
    const page = await browser.newPage({viewport: {width: 1400, height: 1000}, acceptDownloads: true});
    const errors = [], network = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("request", request => {
      if (!["file:", "data:", "blob:"].includes(new URL(request.url()).protocol)) network.push(request.url());
    });
    await page.route("**/*", route => new URL(route.request().url()).protocol === "file:" ? route.continue() : route.abort());
    await page.goto(pathToFileURL(path.join(root, "REVIEW.html")).href, {waitUntil: "load"});
    await page.waitForFunction(() => [...document.images].every(image => image.complete && image.naturalWidth > 0));
    assert.equal(await page.locator("tr[data-item]").count(), counts.review_items);
    assert.equal(await page.locator("svg rect[data-cell]").count(), counts.cells);
    await page.locator("#uncertain-only").check();
    assert.equal(await page.locator("tr[data-item]:visible").count(), counts.uncertain_items);
    await page.locator("#uncertain-only").uncheck();
    const first = page.locator("tr[data-item]").first();
    await first.locator("select").selectOption("correct");
    await first.locator("textarea").fill("PUBLIC_SYNTHETIC_BROWSER_CORRECTION");
    const downloaded = page.waitForEvent("download");
    await page.locator("#download").click();
    await (await downloaded).saveAs(path.join(root, "public-edited.csv"));
    await page.reload({waitUntil: "load"});
    assert(await page.locator("tr[data-item] select").evaluateAll(elements => elements.every(e => e.value === "")));
    assert.equal(errors.length, 0, JSON.stringify(errors));
    assert.equal(network.length, 0);
    console.log("PASS: offline overlays, filtering, CSV export, reload and no network");
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
