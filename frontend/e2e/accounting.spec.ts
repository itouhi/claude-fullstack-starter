import { expect, test, type Locator, type Page } from "@playwright/test";

/**
 * 会計システムの主要導線 E2E (回帰テスト / Vuetify UI 対応)。
 *
 * backend は in-memory のため固有の識別子で自分のデータを検証して決定的にする。
 */

/** 左ナビ (Vuetify drawer) の項目をラベルで開く。 */
async function openTab(page: Page, label: string): Promise<void> {
  await page.locator(".v-navigation-drawer .v-list-item-title", { hasText: label }).first().click();
}

/** v-select を開いて選択肢をタイトルで選ぶ。 */
async function pickSelect(page: Page, select: Locator, optionTitle: string): Promise<void> {
  await select.click();
  await page
    .locator(".v-overlay-container .v-list-item-title", { hasText: optionTitle })
    .first()
    .click();
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".v-navigation-drawer")).toBeVisible();
});

test("仕訳入力 → 仕訳帳に反映され、試算表が貸借一致する", async ({ page }) => {
  await openTab(page, "仕訳入力");
  await page.locator(".header .grow input").fill("E2E現金売上");
  // 借方行: 現金 / 88,000
  await pickSelect(page, page.locator(".lines tbody tr:nth-child(1) td:nth-child(2) .v-select"), "現金");
  await page.locator(".lines tbody tr:nth-child(1) td:nth-child(3) input").fill("88000");
  // 貸方行: 売上高 / 88,000
  await pickSelect(page, page.locator(".lines tbody tr:nth-child(2) td:nth-child(2) .v-select"), "売上高");
  await page.locator(".lines tbody tr:nth-child(2) td:nth-child(3) input").fill("88000");
  await expect(page.locator(".totals")).toContainText("一致");
  await page.locator(".entry-form button[type=submit]").click();

  await expect(page.locator(".journal")).toContainText("E2E現金売上");
  await expect(page.locator(".journal")).toContainText("88,000");

  await openTab(page, "試算表");
  await expect(page.locator(".tb tfoot")).toContainText("貸借一致");
});

test("出納帳: 入金・出金の簡易入力が残高に反映される", async ({ page }) => {
  await openTab(page, "出納帳");
  // 入金 (売上高)
  await pickSelect(page, page.locator(".quick-entry .v-select").nth(0), "入金");
  await pickSelect(page, page.locator(".quick-entry .v-select").nth(1), "売上高");
  await page.locator('.quick-entry input[placeholder="金額"]').fill("70000");
  await page.locator('.quick-entry input[placeholder="摘要"]').fill("E2E入金");
  await page.getByRole("button", { name: "記帳" }).click();
  await expect(page.locator(".book tbody tr", { hasText: "E2E入金" })).toContainText("70,000");

  // 出金 (消耗品費)
  await pickSelect(page, page.locator(".quick-entry .v-select").nth(0), "出金");
  await pickSelect(page, page.locator(".quick-entry .v-select").nth(1), "消耗品費");
  await page.locator('.quick-entry input[placeholder="金額"]').fill("4000");
  await page.locator('.quick-entry input[placeholder="摘要"]').fill("E2E出金");
  await page.getByRole("button", { name: "記帳" }).click();
  await expect(page.locator(".book tbody tr", { hasText: "E2E出金" })).toContainText("4,000");
});

test("売上・売掛: 計上 → 未入金 → 入金消込", async ({ page }) => {
  const party = "E2Eクライアント";
  await openTab(page, "売上・売掛");
  await page.locator('.receivables .register input[placeholder="A社"]').fill(party);
  await page
    .locator(".receivables .register .v-text-field", { hasText: "金額(税込)" })
    .locator("input")
    .fill("132000");
  await page.locator('.receivables .register input[placeholder^="コンサル"]').fill("E2E役務提供");
  await page.getByRole("button", { name: "売上計上" }).click();

  const row = page.locator(".receivables tbody tr", { hasText: party });
  await expect(row).toContainText("132,000");

  await row.getByRole("button", { name: "全額入金" }).click();
  await expect(page.locator(".receivables tbody tr", { hasText: party })).toHaveCount(0);
});

test("経費: 未払計上が未払金一覧に現れる", async ({ page }) => {
  const party = "E2E外注先";
  await openTab(page, "経費");
  await pickSelect(page, page.locator(".expenses .register .v-select", { hasText: "勘定科目" }), "外注工賃");
  await page
    .locator(".expenses .register .v-text-field", { hasText: "金額(税込)" })
    .locator("input")
    .fill("99000");
  await pickSelect(page, page.locator(".expenses .register .v-select", { hasText: "支払方法" }), "未払 (後払い)");
  await page.locator('.expenses .register input[placeholder="C社"]').fill(party);
  await page.locator('.expenses .register input[placeholder^="通信費"]').fill("E2E外注費");
  await page.getByRole("button", { name: "経費計上" }).click();

  await expect(page.locator(".expenses tbody tr", { hasText: party })).toContainText("99,000");
});

test("ダッシュボード: 売上が当期売上高に集計される", async ({ page }) => {
  await openTab(page, "売上・売掛");
  await page.locator('.receivables .register input[placeholder="A社"]').fill("E2Eダッシュ確認");
  await page
    .locator(".receivables .register .v-text-field", { hasText: "金額(税込)" })
    .locator("input")
    .fill("210000");
  await page.locator('.receivables .register input[placeholder^="コンサル"]').fill("E2Eダッシュ売上");
  await page.getByRole("button", { name: "売上計上" }).click();
  await expect(page.locator(".receivables tbody tr", { hasText: "E2Eダッシュ確認" })).toBeVisible();

  await openTab(page, "ダッシュボード");
  const revenueCard = page.locator(".card", { hasText: "当期売上高" });
  await expect(revenueCard.locator(".value")).not.toHaveText("¥0");
});
