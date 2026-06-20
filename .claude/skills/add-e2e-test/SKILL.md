---
name: add-e2e-test
description: Playwright で自動 E2E テスト (commit 済みの回帰テスト) を導入・追加する。実ブラウザでユーザー操作を再生し検証する。verifier-webapp の手動相当検証を回帰自動化する。「E2E」「Playwright テスト」「自動UIテスト」などで起動。
---

# add-e2e-test

**Playwright の自動 E2E テスト**を追加する。`verifier-webapp` (その場の手動相当検証) と違い、
**リポジトリに commit して CI で回す回帰テスト**を作る。

> 出典: 本番 Vue アプリは E2E スイート (Playwright) を持つのが標準 (cloudinary.com / vue prod)。

## verifier-webapp との違い
| | verifier-webapp | add-e2e-test |
|---|---|---|
| 目的 | 変更直後の実機確認 (人/Claude が観測) | **回帰防止** (恒久テスト) |
| 成果 | スクショ・観測ログ | **commit 済みテストコード** |
| 実行 | その都度手動駆動 | CI で自動 (`setup-ci`) |

playwright 本体は frontend に常設済み (verifier-webapp 用)。E2E ランナーは `@playwright/test` を使う。

## 初回セットアップ
1. `npm i -D @playwright/test` (+ ブラウザ `npx playwright install`)。
2. `playwright.config.ts`: `webServer` で dev サーバ (backend+frontend) を自動起動、`baseURL`、`testDir: e2e/`。
3. `package.json` に `"test:e2e": "playwright test"`。

## テストの書き方
- 配置: `frontend/e2e/<feature>.spec.ts`。
- **ユーザー操作で検証** (実ブラウザ):
```ts
import { test, expect } from "@playwright/test";

test("商品を価格でソートできる", async ({ page }) => {
  await page.goto("/products");
  await page.click(".products th.col-price");
  const first = page.locator(".products tbody tr").first();
  await expect(first).toContainText("バナナ"); // 最安が先頭
});
```
- 認証が要る画面はログイン手順を `beforeEach` / storageState で共通化 (`add-auth`)。
- データ依存はシード/フィクスチャを固定し決定的にする。

## CI 連携
- `setup-ci` の frontend ジョブ (または専用ジョブ) に `npx playwright install --with-deps` + `npm run test:e2e` を追加。重いので並列・キャッシュを検討。

## ガードレール
- E2E は**主要導線**に絞る (全網羅しない。細部は単体テスト `add-frontend-test`)。
- セレクタは壊れにくいもの (役割/テキスト/データ属性)。実装詳細に密結合しない。
- 外部ネットワークに依存しない (バックエンドはローカル起動)。
- 命名・フォーマットは `coding-standards`。
