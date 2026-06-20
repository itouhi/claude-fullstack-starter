// 実ブラウザ (Playwright/Chromium headless) で SPA を駆動し、観測結果を JSON で出力する。
// 環境変数で制御:
//   URL           検証対象 (既定 http://localhost:5173)
//   WAIT_SELECTOR 描画完了の目印となる CSS セレクタ (既定 #app)
//   API_MATCH     API ステータスを記録する URL 部分一致 (既定 /api/)
//   SHOT          スクリーンショット出力先 (既定 /tmp/verify-shot.png)
//   PW            playwright モジュールの解決パス。未指定なら cwd 起点で自動探索する
//   ACTIONS       初期描画後に実行する操作の JSON 配列 (任意)。対話プローブ用。
//                 各要素はいずれか:
//                   {"fill": {"selector": ".tasks input", "value": "牛乳"}}
//                   {"click": ".tasks button[type=submit]"}
//                   {"waitFor": ".tasks li"}        // セレクタ出現待ち
//                   {"waitTimeout": 500}            // ミリ秒待ち
const path = require("path");

// playwright は frontend/node_modules にあり、本スクリプトのディレクトリからは
// 解決できない。PW 明示 → cwd 起点の候補 → 素の "playwright" の順に探す。
function resolvePlaywright() {
  const candidates = [
    process.env.PW,
    path.resolve(process.cwd(), "frontend/node_modules/playwright"),
    path.resolve(process.cwd(), "node_modules/playwright"),
    "playwright",
  ].filter(Boolean);
  for (const c of candidates) {
    try {
      require.resolve(c);
      return c;
    } catch {
      /* 次の候補へ */
    }
  }
  throw new Error(
    "playwright を解決できません。frontend で `npm i -D playwright` を実行するか PW を指定してください",
  );
}

const { chromium } = require(resolvePlaywright());

const targetUrl = process.env.URL || "http://localhost:5173";
const WAIT_SELECTOR = process.env.WAIT_SELECTOR || "#app";
const API_MATCH = process.env.API_MATCH || "/api/";
const SHOT = process.env.SHOT || "/tmp/verify-shot.png";
const ACTIONS = process.env.ACTIONS ? JSON.parse(process.env.ACTIONS) : [];

async function runAction(page, a) {
  if (a.fill) return page.fill(a.fill.selector, a.fill.value);
  if (a.click) return page.click(a.click);
  if (a.waitFor) return page.waitForSelector(a.waitFor, { timeout: 8000 });
  if (a.waitTimeout) return page.waitForTimeout(a.waitTimeout);
  throw new Error("未知の action: " + JSON.stringify(a));
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const consoleErrors = [];
  const apiStatuses = [];
  page.on("console", (m) => {
    if (m.type() === "error") consoleErrors.push(m.text());
  });
  page.on("pageerror", (e) => consoleErrors.push("pageerror: " + e.message));
  page.on("response", (r) => {
    if (r.url().includes(API_MATCH))
      apiStatuses.push({ method: r.request().method(), url: r.url(), status: r.status() });
  });

  await page.goto(targetUrl, { waitUntil: "networkidle" });
  await page.waitForSelector(WAIT_SELECTOR, { timeout: 10000 });
  await page.waitForTimeout(800);

  // 対話プローブ (任意)
  for (const a of ACTIONS) await runAction(page, a);
  if (ACTIONS.length) await page.waitForTimeout(500);

  const bodyText = await page.locator("body").innerText();
  await page.screenshot({ path: SHOT, fullPage: true });

  console.log(
    JSON.stringify(
      { url: targetUrl, apiStatuses, consoleErrors, screenshot: SHOT, bodyText },
      null,
      2,
    ),
  );
  await browser.close();
})().catch((e) => {
  console.error("DRIVE_ERROR: " + e.message);
  process.exit(1);
});
