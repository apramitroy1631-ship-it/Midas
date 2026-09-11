// Drives the real running BuildX console and captures screenshots for the
// UI/UX demo design document. Every screen shown is the actual app — nothing
// here is mocked or hand-drawn.
import { chromium } from "playwright";
import { mkdirSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname, "screens");
mkdirSync(OUT, { recursive: true });

const BASE = "http://localhost:5175";
const API = "http://127.0.0.1:8100";
const VERTEX_KEY = process.argv[2];
const NORTHWIND_KEY = process.argv[3];

const VIEWPORT = { width: 1440, height: 900 };

async function shot(page, name, opts = {}) {
  await page.waitForTimeout(opts.wait ?? 250);
  await page.screenshot({ path: path.join(OUT, name + ".png"), fullPage: !!opts.fullPage });
  console.log("captured", name);
}

async function seedConnection(page, key, label) {
  // Bypass the connect form by writing straight into localStorage, then reload.
  await page.goto(BASE);
  await page.evaluate(
    ({ key, label, base }) => {
      const conn = {
        id: crypto.randomUUID(),
        label,
        apiKey: key,
        baseUrl: base,
        color: "#6ea8fe",
      };
      const list = [conn];
      localStorage.setItem("buildx.connections", JSON.stringify(list));
      localStorage.setItem("buildx.active", JSON.stringify(conn.id));
      localStorage.setItem("buildx.theme", JSON.stringify("dark"));
    },
    { key, label, base: API }
  );
  await page.reload();
  await page.waitForSelector("text=Mission control", { timeout: 15000 });
}

async function clickNav(page, label) {
  // Nav buttons render an icon glyph alongside the label, so the accessible
  // name is never exactly the label — match it as a substring instead.
  await page.locator(".nav-item", { hasText: label }).first().click();
  await page.waitForTimeout(400);
}

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: VIEWPORT, deviceScaleFactor: 2 });
  const page = await context.newPage();

  // ---- 1. Connect screen (fresh, no localStorage) ----
  await page.goto(BASE);
  await page.waitForSelector("text=BuildX Console");
  await shot(page, "01-connect");

  // Fill the form visually (not via storage) for an authentic capture. Uses a
  // placeholder-shaped string, not a real key — this screenshot ships in a
  // shareable PDF and a real credential has no business appearing in it.
  await page.getByPlaceholder("bx_live_…").fill("bx_live_" + "•".repeat(43));
  await shot(page, "01b-connect-filled");

  // ---- Connect as Vertex Robotics (product / B2B robotics tenant) ----
  await seedConnection(page, VERTEX_KEY, "Vertex Robotics");

  // ---- 2. Mission control / Overview ----
  await shot(page, "02-overview", { wait: 600 });

  // ---- 3. Launch — idle state ----
  await clickNav(page, "Launch run");
  await shot(page, "03-launch-idle");

  // ---- 4. Launch — live run in progress ----
  await page.getByRole("button", { name: "▶ Launch autonomous run" }).click();
  await page.waitForSelector("text=Revision cycle", { timeout: 20000 }).catch(() => {});
  await shot(page, "04-launch-running", { wait: 500 });

  // Wait for the run to finish so we can show the full trace + outcome.
  await page.waitForSelector("text=Outcome", { timeout: 30000 }).catch(() => {});
  await shot(page, "05-launch-complete", { fullPage: true, wait: 600 });

  // Expand the QA step to show a node detail panel. Scroll it near the TOP
  // of the viewport first (block:"start"), not just "into view" — the
  // expansion adds a few hundred px below the card, and a bare click()
  // only guarantees the card's own top edge is visible, which previously
  // left the score meters cut off below the fold.
  const qaCard = page.locator(".rail-card", { hasText: "QA Reviewer" }).last();
  await qaCard.evaluate((el) => el.scrollIntoView({ block: "start" }));
  await page.mouse.wheel(0, -120); // small breathing room above the card
  await qaCard.click().catch(() => {});
  await shot(page, "06-launch-qa-detail", { wait: 400 });

  // ---- 7. Runs history + drawer ----
  await clickNav(page, "Runs");
  await shot(page, "07-runs-list", { wait: 400 });
  const firstRow = page.locator(".table tbody tr").first();
  await firstRow.click().catch(() => {});
  await page.waitForSelector(".drawer", { timeout: 8000 }).catch(() => {});
  await shot(page, "08-runs-drawer", { wait: 500 });
  await page.keyboard.press("Escape");

  // ---- 9. Content library ----
  await clickNav(page, "Content library");
  await shot(page, "09-library", { wait: 400 });

  // ---- 10. Brands ----
  await clickNav(page, "Brands");
  await shot(page, "10-brands", { wait: 400 });
  const brandEdit = page.getByRole("button", { name: "Edit" }).first();
  await brandEdit.click().catch(() => {});
  await page.waitForSelector(".drawer", { timeout: 8000 }).catch(() => {});
  await shot(page, "11-brands-drawer", { wait: 400 });
  await page.keyboard.press("Escape");

  // ---- 12. Audit log ----
  await clickNav(page, "Decision log");
  await shot(page, "12-audit", { wait: 400 });

  // ---- 13. Settings ----
  await clickNav(page, "Settings");
  await shot(page, "13-settings", { fullPage: true, wait: 400 });

  // ---- 14. Tenant switcher open ----
  // Reconnect a second tenant so the switcher has two entries to show.
  await page.evaluate(
    ({ key, base }) => {
      const list = JSON.parse(localStorage.getItem("buildx.connections") || "[]");
      list.push({
        id: crypto.randomUUID(),
        label: "Northwind Talent",
        apiKey: key,
        baseUrl: base,
        color: "#b98cff",
      });
      localStorage.setItem("buildx.connections", JSON.stringify(list));
    },
    { key: NORTHWIND_KEY, base: API }
  );
  await page.reload();
  await page.waitForSelector("text=Mission control", { timeout: 15000 });
  await page.locator(".tenant-switch").click();
  await page.waitForTimeout(300);
  await shot(page, "14-tenant-switcher");

  // ---- 15. Light theme, overview ----
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: /Dark|Light/ }).click();
  await page.waitForTimeout(300);
  await shot(page, "15-light-theme", { wait: 300 });

  await browser.close();
  console.log("done");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
