// Public synthetic original only. Run via test_pdf_review_visual.py.
const assert = require("node:assert/strict");
const path = require("node:path");
const {chromium} = require(path.join(process.env.ML30_NODE_MODULES, "playwright"));

(async () => {
  const browser = await chromium.launch({channel: "msedge", headless: true, args: ["--disable-gpu"]});
  try {
    const page = await browser.newPage({viewport: {width: 1400, height: 1000}});
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.route("**/*", route => new URL(route.request().url()).origin === new URL(process.argv[2]).origin ? route.continue() : route.abort());
    await page.goto(process.argv[2], {waitUntil: "domcontentloaded"});
    const ready = async () => {
      try { await page.waitForFunction(() => document.querySelector("#capture-status").textContent.includes("capture enabled"), undefined, {timeout: 10000}); }
      catch (error) { console.error(await page.locator("#capture-status").textContent(), errors); throw error; }
    };
    await ready();
    // Locate the actual black rectangle in the rendered canvas; never infer from a JSON oracle alone.
    const painted = await page.locator("#page-canvas").evaluate(canvas => {
      const {data} = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height);
      let left = canvas.width, top = canvas.height, right = 0, bottom = 0;
      for (let y = 0; y < canvas.height; y++) for (let x = 0; x < canvas.width; x++) {
        const offset = 4 * (y * canvas.width + x);
        if (data[offset + 3] && data[offset] < 64 && data[offset + 1] < 64 && data[offset + 2] < 64) {
          left = Math.min(left, x); top = Math.min(top, y); right = Math.max(right, x + 1); bottom = Math.max(bottom, y + 1);
        }
      }
      return [left / canvas.width, top / canvas.height, right / canvas.width, bottom / canvas.height];
    });
    assert(painted[2] > painted[0] && painted[3] > painted[1], "actual vector rectangle must render");
    const readBox = async () => {
      const text = await page.locator("#measured-bbox").textContent();
      assert(text.startsWith("PDF bbox:"), text);
      return JSON.parse(text.slice(text.indexOf("[")));
    };
    const close = (actual, expected, tolerance = 0.6) => actual.forEach((v, i) => assert(Math.abs(v - expected[i]) <= tolerance, `${actual} != ${expected}`));
    const draw = async (box = painted) => {
      await page.locator("#visual-mode").selectOption("draw");
      await page.locator("#visual-scroll").scrollIntoViewIfNeeded();
      await page.locator("#visual-scroll").evaluate((element, box) => {
        const canvas = element.querySelector("canvas");
        element.scrollLeft = Math.max(0, box[0] * canvas.clientWidth - 15);
        element.scrollTop = Math.max(0, box[1] * canvas.clientHeight - 15);
      }, box);
      const surface = await page.locator("#page-canvas").boundingBox();
      await page.mouse.move(surface.x + box[0] * surface.width, surface.y + box[1] * surface.height);
      await page.mouse.down();
      await page.mouse.move(surface.x + box[2] * surface.width, surface.y + box[3] * surface.height, {steps: 10});
      await page.mouse.up();
      close(await readBox(), [60, 100, 180, 200]);
    };
    await draw();
    await page.locator("#visual-zoom").selectOption("2");
    await draw();
    await page.setViewportSize({width: 1100, height: 820});
    await page.locator("#visual-zoom").selectOption("1.5");
    await draw();
    await page.locator("#cancel-selection").click();
    assert.equal(await page.locator("#measured-bbox").textContent(), "No rectangle selected");
    await page.locator("#visual-scroll").scrollIntoViewIfNeeded();
    const blankSurface = await page.locator("#page-canvas").boundingBox();
    await page.mouse.click(blankSurface.x + painted[0] * blankSurface.width, blankSurface.y + painted[1] * blankSurface.height);
    assert.equal(await page.locator("#measured-bbox").textContent(), "No rectangle selected", "zero area must be rejected");
    assert(await page.locator("#assign-geometry").isDisabled());
    await page.locator("#undo-selection").click();
    close(await readBox(), [60, 100, 180, 200]);
    // Move and resize through real pointer events, then undo both edits.
    await page.locator("#visual-scroll").scrollIntoViewIfNeeded();
    let surface = await page.locator("#page-canvas").boundingBox();
    const x = surface.x + (painted[0] + 0.03) * surface.width;
    const y = surface.y + (painted[1] + 0.03) * surface.height;
    await page.locator("#visual-mode").selectOption("move");
    await page.mouse.move(x, y); await page.mouse.down(); await page.mouse.move(x + 6, y + 6); await page.mouse.up();
    assert.notDeepEqual(await readBox(), [60, 100, 180, 200]);
    await page.locator("#undo-selection").click();
    close(await readBox(), [60, 100, 180, 200]);
    await page.locator("#visual-mode").selectOption("resize");
    await page.locator("#visual-scroll").scrollIntoViewIfNeeded();
    surface = await page.locator("#page-canvas").boundingBox();
    const endX = surface.x + painted[2] * surface.width, endY = surface.y + painted[3] * surface.height;
    await page.mouse.move(endX, endY); await page.mouse.down(); await page.mouse.move(endX - 8, endY - 8); await page.mouse.up();
    await page.locator("#undo-selection").click();
    close(await readBox(), [60, 100, 180, 200]);
    await page.locator("#add-region").click();
    await page.locator("#regions").fill(JSON.stringify([{region_id: "public-human-region", table_id: null, bbox_pdf_user_space_points: null, notes: "preserve me"}]));
    await page.locator("#refresh-targets").click();
    await page.locator("#assign-geometry").click();
    await page.waitForFunction(() => document.querySelector("#message").textContent.includes("Rectangle explicitly assigned"));
    await ready();
    close(JSON.parse(await page.locator("#regions").inputValue())[0].bbox_pdf_user_space_points, [60, 100, 180, 200]);
    assert.equal(JSON.parse(await page.locator("#regions").inputValue())[0].notes, "preserve me");
    await page.reload({waitUntil: "domcontentloaded"}); await ready();
    await page.locator("#load-target").click();
    close(await readBox(), [60, 100, 180, 200]);
    // Explicit table/cell assignments leave identities and semantics unfilled.
    await page.locator("#add-table").click();
    await page.locator("#refresh-targets").click();
    await page.locator("#geometry-target").selectOption(JSON.stringify({kind: "table", table: 0}));
    await page.locator("#assign-geometry").click();
    await page.waitForFunction(() => document.querySelector("#message").textContent.includes("Rectangle explicitly assigned")); await ready();
    await page.locator("#geometry-target").selectOption(JSON.stringify({kind: "table", table: 0}));
    await page.locator("#load-target").click();
    await page.locator("#add-cell").click();
    await page.locator("#geometry-target").selectOption(JSON.stringify({kind: "cell", table: 0, cell: 0}));
    await page.locator("#assign-geometry").click();
    await page.waitForFunction(() => document.querySelector("#message").textContent.includes("Rectangle explicitly assigned")); await ready();
    const table = JSON.parse(await page.locator("#tables").inputValue())[0];
    close(table.bbox_pdf_user_space_points, [60, 100, 180, 200]);
    close(table.cells[0].bbox_pdf_user_space_points, [60, 100, 180, 200]);
    assert.equal(table.cells[0].row, null); assert.equal(table.cells[0].literal_text, null);
    page.once("dialog", dialog => dialog.accept());
    await page.locator("#undo-assignment").click();
    await page.waitForFunction(() => document.querySelector("#message").textContent.includes("assignment undone")); await ready();
    assert.equal(JSON.parse(await page.locator("#tables").inputValue())[0].cells.length, 0);
    assert(await page.locator("#reveal").isDisabled());
    assert(Object.values(JSON.parse(await page.locator("#reviewer").inputValue())).every(v => v === null));
    assert.deepEqual(errors, []);
    console.log("Rendered mouse path PASS: known rectangle, zoom, scroll, resize, adjust, cancel/undo, region/table/cell save/reload, blinding");
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
