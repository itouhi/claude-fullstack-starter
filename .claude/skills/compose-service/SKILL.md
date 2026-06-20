---
name: compose-service
description: 既存の垂直スライス機能 (users-list/tasks/notes/products 等) をマニフェストで選んで1つのサービス (ナビ付き SPA + 横断集約 API) に束ねる。「サービスを作る」「機能をまとめる」「ダッシュボードに統合」などで起動。
---

# compose-service

複数の機能を**1つのサービス**に組み立てるオーケストレーション。
各機能は `add-*` / `run-dev-cycle` で作った**垂直スライス** (backend router + frontend service/component) である前提。

> ベースにした考え方: モジュラーモノリス＋垂直スライス / BFF (API集約) / App Shell コンポジション / Feature Flag。
> 出典: milanjovanovic.tech, samnewman.io (BFF), learn.microsoft.com (BFF), martinfowler.com (feature toggles)。

## 入力として確認すること
1. **サービス名** — kebab-case (例: `admin-console`)
2. **束ねる機能** — 既存機能のキー一覧 (例: users-list, tasks, notes, products)
3. **横断集約の要否** — ダッシュボード等の BFF エンドポイントを作るか

## 構成方針
- **frontend**: App Shell (ナビ＋テーマ＋`<router-view>`) に選択機能を合成。vue-router でルート切替。
- **backend**: 選択機能の router のみ登録 (モジュラーモノリス)。必要なら横断集約 `GET /dashboard` (BFF)。
- **選択**: サービスマニフェストで宣言。`enabled: false` の機能は登録もルート生成もしない (Feature Flag)。
- **境界**: 機能モジュールは互いの内部状態に直接触らない。集約は BFF 側で各機能の公開関数/APIを呼ぶ。

## サービスマニフェスト (宣言)
`frontend/src/service.config.ts` に1ファイルで定義する。
```ts
import type { Component } from "vue";

export interface ServiceFeature {
  key: string;        // 機能キー
  label: string;      // ナビ表示名
  path: string;       // ルートパス (例 "/tasks")
  component: () => Promise<{ default: Component }>;  // 遅延 import (vue-router/vue-tsc が通る型)
  enabled: boolean;   // Feature Flag
}

export const serviceName = "admin-console";
export const features: ServiceFeature[] = [
  { key: "tasks", label: "タスク", path: "/tasks",
    component: () => import("@/components/TasksList.vue"), enabled: true },
  // ...
];
```

## 手順
1. **マニフェスト作成** — 束ねる機能を `service.config.ts` に列挙 (enabled で取捨)。
2. **frontend App Shell**:
   - `vue-router` を導入し、`src/router.ts` で **enabled な機能のみ**からルートを生成 (+ `/dashboard`)。
   - `App.vue` をシェル化: ナビ (`<router-link>` をマニフェストから生成) ＋ `<router-view />`。
   - `main.ts` で `app.use(router)`。
3. **backend 組立**:
   - `app/api/__init__.py` でサービスに含む router のみ登録。
   - 集約する場合 `app/api/dashboard.py` に `GET /dashboard` を作り、各機能の件数/サマリを**集約**して返す (response_model 指定)。
4. **サービスドキュメント** — `docs/services/<サービス名>/README.md` に概要・含む機能・マニフェスト・各機能ドキュメントへのリンク (トレーサビリティ束ね) を `write-dev-docs` 方針で記載。
5. **統合検証** — `verifier-webapp` でルート横断 E2E:
   - ナビ各リンクをクリック (`ACTIONS`) し、各機能が描画されること。
   - `/dashboard` が集約値を表示すること。
6. **レビュー** — 組立差分を `/code-review` でレビューし、指摘を解消する (品質関門)。
7. **コミット** — `push-changes` で関心事ごとに分割。

## ガードレール
- 機能間で**内部ストアを直接共有しない**。集約は BFF (`/dashboard`) で各機能の公開関数/API を介して行う。
- サービス横断のフロント状態 (ログインユーザー等) は `add-store` スキル (Pinia) で共有する。
- マニフェストを単一情報源とし、ナビ・ルート・(必要なら) backend 登録をそこから導く。手で二重管理しない。
- `enabled: false` の機能はルートもナビも出さない (deploy と release の分離)。
- 実装は `coding-standards` (命名/docstring/TSDoc・工程ID) と CLAUDE.md に従う。
- 検証は `sandbox` で行い、UI は `verifier-webapp` で実ブラウザ確認する。
- 関連スキル: `add-*` / `run-dev-cycle` (機能作成) / `write-dev-docs` (文書化) / `verifier-webapp` (検証) / `push-changes`。
