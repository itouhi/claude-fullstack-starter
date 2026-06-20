---
name: add-frontend-test
description: frontend に Vitest + Vue Testing Library で単体テストを導入・追加する。コンポーネント/コンポーザブルの描画・操作・状態を検証する。「フロントのテスト」「Vitest」「コンポーネントテスト」などで起動。
---

# add-frontend-test

frontend の単体テストを **Vitest + @testing-library/vue** で導入・追加する。
(現状 frontend テストは未導入。必要になったら本スキルで入れる — CLAUDE.md)

> 出典: Unit Testing Vue 3 with Vitest and Testing Library (medium.com)。

## 初回セットアップ
1. 依存追加: `npm i -D vitest @vue/test-utils @testing-library/vue jsdom`。
2. `vite.config.ts` (または `vitest.config.ts`) に test 設定 (型付けのため先頭に vitest の参照を追加):
   ```ts
   /// <reference types="vitest/config" />
   // defineConfig({...}) 内に:
   test: { environment: "jsdom", globals: true },
   ```
3. `package.json` に `"test": "vitest run"`, `"test:watch": "vitest"`。
4. `eslint`/`tsconfig` がテストファイル (`*.spec.ts`, `*.test.ts`) を含むことを確認。

## テストの書き方
- 配置: コンポーネント隣接 `Foo.spec.ts` か `src/__tests__/`。
- **振る舞いで検証** (実装詳細でなく): 描画テキスト・ユーザー操作 (click/input) → 期待結果。
```ts
import { render, screen, fireEvent } from "@testing-library/vue";
import TasksList from "@/components/TasksList.vue";

test("入力して追加するとAPIが呼ばれ一覧に反映", async () => {
  // fetch をモック (vi.stubGlobal / msw 等)
  render(TasksList);
  await fireEvent.update(screen.getByPlaceholderText("新しいタスク"), "牛乳");
  await fireEvent.click(screen.getByText("追加"));
  expect(await screen.findByText("牛乳")).toBeTruthy();
});
```
- API 通信は `vi.fn()` / `vi.stubGlobal("fetch", ...)` か MSW でモックし、ネットワークに依存しない。
- Pinia を使う場合は各テストで `setActivePinia(createPinia())` を実行 (→ `add-store`)。

## 役割分担
- **単体 (本スキル/Vitest)**: ロジック・描画・状態を高速に検証。
- **実機/E2E**: `verifier-webapp` (手動相当の実ブラウザ観測) / `add-e2e-test` (Playwright 自動回帰)。
- CI 連携: `setup-ci` の frontend ジョブに `npm run test` を追加する。

## ガードレール
- テストは振る舞い基準。実装詳細 (内部 ref 名など) に結合させない。
- 命名・フォーマットは `coding-standards` (eslint/prettier はテストにも適用)。
- ネットワーク/時刻などの外部依存はモックし、決定的にする。
