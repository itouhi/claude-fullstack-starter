import { expect, test, type Page } from "@playwright/test";

/**
 * 会計システムの残り全機能の E2E (回帰テスト / Vuetify UI 対応)。
 *
 * CSV取込・総勘定元帳・損益計算書・貸借対照表・固定資産・青色申告決算書・
 * 消費税・証憑保存・データ管理 (CSVエクスポート・年度繰越) をカバーする。
 */

async function openTab(page: Page, label: string): Promise<void> {
  await page.locator(".v-navigation-drawer .v-list-item-title", { hasText: label }).first().click();
}

/** 売上・売掛フォームから税込売上を1件計上する (消費税/決算書のデータ作り)。 */
async function createSale(page: Page, party: string, amount: number): Promise<void> {
  await openTab(page, "売上・売掛");
  await page.locator('.receivables .register input[placeholder="A社"]').fill(party);
  await page
    .locator(".receivables .register .v-text-field", { hasText: "金額(税込)" })
    .locator("input")
    .fill(String(amount));
  await page.locator('.receivables .register input[placeholder^="コンサル"]').fill(`${party}売上`);
  await page.getByRole("button", { name: "売上計上" }).click();
  await expect(page.locator(".receivables tbody tr", { hasText: party })).toBeVisible();
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".v-navigation-drawer")).toBeVisible();
});

test("CSV取込: 明細を取り込み、候補を確定して仕訳化する", async ({ page }) => {
  await openTab(page, "CSV取込");
  await page.getByRole("button", { name: "CSV を取り込む" }).click();
  await expect(page.locator(".candidates tbody tr").first()).toBeVisible();
  await page.locator(".candidates tbody tr").first().getByRole("button", { name: "確定" }).click();
  await expect(page.locator(".candidates tbody tr").first()).toContainText("確定");
});

test("総勘定元帳: 科目を選ぶと明細が表示される", async ({ page }) => {
  await openTab(page, "総勘定元帳");
  await expect(page.locator(".gl")).toBeVisible();
  await expect(page.locator(".gl thead")).toContainText("残高");
});

test("損益計算書: 当期純利益が表示される", async ({ page }) => {
  await openTab(page, "損益計算書");
  await expect(page.locator(".pl")).toContainText("当期純利益");
});

test("貸借対照表: 資産=負債+純資産で貸借一致する", async ({ page }) => {
  await openTab(page, "貸借対照表");
  await expect(page.locator(".bs .check")).toContainText("貸借一致");
});

test("固定資産: 登録し、償却予定表を表示する", async ({ page }) => {
  await openTab(page, "固定資産");
  await page.locator('.fixed-assets .register input[placeholder^="資産名"]').fill("E2E備品");
  await page
    .locator(".fixed-assets .register .v-text-field", { hasText: "取得日" })
    .locator("input")
    .fill("2026-04-01");
  await page
    .locator(".fixed-assets .register .v-text-field", { hasText: "取得価額" })
    .locator("input")
    .fill("300000");
  await page
    .locator(".fixed-assets .register .v-text-field", { hasText: "耐用年数" })
    .locator("input")
    .fill("5");
  await page.getByRole("button", { name: "資産を登録" }).click();

  const row = page.locator(".assets tbody tr", { hasText: "E2E備品" });
  await expect(row).toContainText("300,000");
  await row.getByRole("button", { name: "予定表" }).click();
  await expect(page.locator(".schedule table tbody tr").first()).toBeVisible();
});

test("青色申告決算書: PL/月別売上/減価償却を集約表示する", async ({ page }) => {
  await createSale(page, "E2E青色", 165000);
  await openTab(page, "青色申告決算書");
  await expect(page.locator(".blue-return")).toContainText("所得金額");
  await expect(page.locator(".blue-return")).toContainText("月別売上金額");
  await expect(page.locator(".blue-return")).toContainText("減価償却費の計算");
});

test("消費税: 簡易課税の納付税額を集計し確定できる", async ({ page }) => {
  await createSale(page, "E2E消費税", 110000); // 内税 10,000
  await openTab(page, "消費税");
  await page.locator(".tax .year input").fill(String(new Date().getFullYear()));
  await page.locator(".tax .year input").dispatchEvent("change");
  await expect(page.locator(".tax tfoot")).toBeVisible();
  await expect(page.locator(".tax tfoot .highlight")).not.toHaveText("0");
  await page.getByRole("button", { name: "納付額を確定" }).click();
  await expect(page.locator(".tax .ok")).toContainText("計上しました");
});

test("証憑保存: 登録し電帳法3キーで検索できる", async ({ page }) => {
  const party = "E2E証憑商店";
  await openTab(page, "証憑保存");
  await page
    .locator(".vouchers .register .v-text-field", { hasText: "取引日" })
    .locator("input")
    .fill("2026-03-15");
  await page
    .locator(".vouchers .register .v-text-field", { hasText: "金額" })
    .first()
    .locator("input")
    .fill("33000");
  await page.locator('.vouchers .register input[placeholder="ABC商事"]').fill(party);
  await page.locator(".vouchers .register").getByRole("button", { name: "登録" }).click();
  await expect(page.locator(".results tbody tr", { hasText: party })).toContainText("33,000");

  await page.locator('.vouchers .search input[placeholder="部分一致"]').fill(party);
  await page.locator(".vouchers .search").getByRole("button", { name: "検索" }).click();
  await expect(page.locator(".results tbody tr", { hasText: party })).toBeVisible();
});

test("データ管理: CSVエクスポートと年度繰越", async ({ page }) => {
  await openTab(page, "データ管理");
  await expect(page.locator(".export-link")).toHaveCount(4);
  await expect(page.locator(".export-link").first()).toHaveAttribute("href", /export\/journal/);

  await page.locator(".data-mgmt section:nth-child(2) .year input").fill("2026");
  await page.getByRole("button", { name: "繰越内容を確認" }).click();
  await expect(page.locator(".preview")).toContainText("期首元入金");
  await page.locator(".preview").getByRole("button", { name: "この内容で繰越を実行" }).click();
  await expect(page.locator(".data-mgmt .ok")).toContainText("繰越");
});
