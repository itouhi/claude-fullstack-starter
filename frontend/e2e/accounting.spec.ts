import { expect, test, type Page } from "@playwright/test";

/**
 * 会計システムの主要導線 E2E (回帰テスト)。
 *
 * backend は in-memory で起動するため、各テストは固有の識別子 (取引先名・摘要) を
 * 使い、自分が作ったデータを対象に検証することで共有状態に影響されず決定的になる。
 */

/** ナビのタブをラベルで開く。 */
async function openTab(page: Page, label: string): Promise<void> {
  await page.getByRole("button", { name: label, exact: true }).click();
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("nav button").first()).toBeVisible();
});

test("仕訳入力 → 仕訳帳に反映され、試算表が貸借一致する", async ({ page }) => {
  await openTab(page, "仕訳入力");
  await page.locator(".header .grow input").fill("E2E現金売上");
  await page.locator(".lines tbody tr:nth-child(1) td:nth-child(2) select").selectOption("101");
  await page.locator(".lines tbody tr:nth-child(1) td:nth-child(3) input").fill("88000");
  await page.locator(".lines tbody tr:nth-child(2) td:nth-child(2) select").selectOption("500");
  await page.locator(".lines tbody tr:nth-child(2) td:nth-child(3) input").fill("88000");
  await expect(page.locator(".totals")).toContainText("一致");
  await page.locator(".entry-form button[type=submit]").click();

  // 登録後は仕訳帳タブに遷移し、登録内容が表示される
  await expect(page.locator(".journal")).toContainText("E2E現金売上");
  await expect(page.locator(".journal")).toContainText("88,000");

  // 試算表は常に貸借一致
  await openTab(page, "試算表");
  await expect(page.locator(".tb tfoot")).toContainText("貸借一致");
});

test("出納帳: 入金・出金の簡易入力が残高に反映される", async ({ page }) => {
  await openTab(page, "出納帳");
  // 入金 (売上高)
  await page.locator(".quick-entry select").nth(0).selectOption("receipt");
  await page.locator(".quick-entry select").nth(1).selectOption("500");
  await page.locator('.quick-entry input[type=number]').fill("70000");
  await page.locator('.quick-entry input[placeholder="摘要"]').fill("E2E入金");
  await page.locator(".quick-entry button[type=submit]").click();
  await expect(page.locator(".book")).toContainText("E2E入金");

  // 出金 (消耗品費)
  await page.locator(".quick-entry select").nth(0).selectOption("payment");
  await page.locator(".quick-entry select").nth(1).selectOption("608");
  await page.locator('.quick-entry input[type=number]').fill("4000");
  await page.locator('.quick-entry input[placeholder="摘要"]').fill("E2E出金");
  await page.locator(".quick-entry button[type=submit]").click();

  // 入金 70,000 / 出金 4,000 がそれぞれの行に計上される
  // (現金残高は他テストの影響を受けるため、自分が作った行の金額で検証する)
  await expect(page.locator(".book tbody tr", { hasText: "E2E入金" })).toContainText("70,000");
  await expect(page.locator(".book tbody tr", { hasText: "E2E出金" })).toContainText("4,000");
});

test("売上・売掛: 計上 → 未入金 → 入金消込", async ({ page }) => {
  const party = "E2Eクライアント";
  await openTab(page, "売上・売掛");
  await page.locator('.receivables .register input[placeholder="A社"]').fill(party);
  await page.locator(".receivables .register input[type=number]").fill("132000");
  await page.locator('.receivables .register input[placeholder^="コンサル"]').fill("E2E役務提供");
  await page.locator(".receivables .register button[type=submit]").click();

  // 未入金一覧に取引先が現れる
  const row = page.locator(".receivables tbody tr", { hasText: party });
  await expect(row).toContainText("132,000");

  // 全額入金で消し込むと一覧から消える
  await row.getByRole("button", { name: "全額入金" }).click();
  await expect(page.locator(".receivables tbody tr", { hasText: party })).toHaveCount(0);
});

test("経費: 未払計上が未払金一覧に現れる", async ({ page }) => {
  const party = "E2E外注先";
  await openTab(page, "経費");
  // 勘定科目: 外注工賃 (611)
  await page.locator(".expenses .register select", { hasText: "外注工賃" }).selectOption("611");
  await page.locator(".expenses .register input[type=number]").fill("99000");
  // 支払方法: 未払 (305)
  await page.locator(".expenses .register select", { hasText: "現金" }).selectOption("305");
  await page.locator('.expenses .register input[placeholder="C社"]').fill(party);
  await page.locator('.expenses .register input[placeholder^="通信費"]').fill("E2E外注費");
  await page.locator(".expenses .register button[type=submit]").click();

  await expect(page.locator(".expenses tbody tr", { hasText: party })).toContainText("99,000");
});

test("ダッシュボード: 売上が当期売上高に集計される", async ({ page }) => {
  // 固有の売上を計上
  await openTab(page, "売上・売掛");
  await page.locator('.receivables .register input[placeholder="A社"]').fill("E2Eダッシュ確認");
  await page.locator(".receivables .register input[type=number]").fill("210000");
  await page.locator('.receivables .register input[placeholder^="コンサル"]').fill("E2Eダッシュ売上");
  await page.locator(".receivables .register button[type=submit]").click();
  await expect(page.locator(".receivables tbody tr", { hasText: "E2Eダッシュ確認" })).toBeVisible();

  // ダッシュボードの当期売上高が 0 でない (集計反映)
  await openTab(page, "ダッシュボード");
  const revenueCard = page.locator(".card", { hasText: "当期売上高" });
  await expect(revenueCard.locator(".value")).not.toHaveText("¥0");
});
