# Project conventions for Claude Code

## スタック
- **Backend:** FastAPI (Python 3.14) — `backend/`
- **Frontend:** Vue 3 + Vite + TypeScript — `frontend/`
- **環境:** VSCode Dev Container (Ubuntu 22.04)

## 既存のスキル

機能追加時はまず `.claude/skills/` の該当スキルを確認すること:
- `add-api-endpoint` — FastAPI エンドポイント追加
- `add-vue-component` — Vue SFC 追加
- `add-fullstack-feature` — フル機能追加 (backend + frontend)
- `write-dev-docs` — 開発工程ドキュメント作成 (要求事項〜リリース、`docs/<機能名>/` 配下)
- `push-changes` — 変更を関心事ごとにコミット分割し、まとめてブランチへ push
- `run-dev-cycle` — 機能を開発工程に沿って半自動で回す (文書化+実装+テストのオーケストレーション)
- `verifier-webapp` — UI/API を実ブラウザ (Playwright) で動作確認
- `coding-standards` — 命名規則・仕様コメント(docstring/TSDoc)・フォーマットの規約 (ruff D / eslint naming で機械強制)
- `compose-service` — 複数機能をマニフェストで束ね1サービス (vue-router App Shell + BFF集約) に組み立てる
- `setup-ci` — GitHub Actions で品質チェック (ruff/pytest/lint/type-check) と依存監査を自動化
- `add-persistence` — in-memory を実 DB 化 (SQLModel/SQLAlchemy + Alembic マイグレーション)
- `add-frontend-test` — frontend に Vitest + Testing Library で単体テストを導入
- `add-auth` — JWT + RBAC の本格認証・認可 (固定トークンを置換)
- `add-store` — frontend の状態管理 (Pinia, 機能単位 store)
- `add-observability` — 構造化ログ・本番安全なエラーハンドリング・基本メトリクス
- `add-e2e-test` — Playwright の自動 E2E (回帰テスト, verifier-webapp の手動を自動化)
- `audit-deps` — 依存脆弱性監査 (npm audit / pip-audit, SCA)

### スキル体系 (補完関係)
規模に応じて選ぶ。下位スキルを上位がオーケストレーションし、横断/基盤スキルが全段に効く。
```
横断 (全段に効く):
  coding-standards(規約/機械強制) ・ write-dev-docs(工程文書) ・ verifier-webapp(実機検証)
  ・ setup-ci(CI自動化) ・ audit-deps(依存監査) ・ push-changes(コミット&push)

基盤 (機能の土台。必要になったら導入):
  add-persistence(DB/移行) ・ add-auth(認証/認可) ・ add-store(状態) ・ add-observability(ログ/エラー)

build (1機能を作る):
  add-api-endpoint / add-vue-component / add-fullstack-feature
  └ テスト: add-frontend-test(単体) ・ add-e2e-test(回帰E2E) ・ verifier-webapp(手動相当)
   ↑ まとめて回す
通す  : run-dev-cycle (要求〜テストを doc→build→review→verify→push でゲート付き)
   ↑ 複数を束ねる
サービス: compose-service (複数機能 → App Shell + BFF集約の1サービス)
```
- 単発のAPI/画面 → `add-*`。要求〜テストまで通す → `run-dev-cycle`。機能群をサービス化 → `compose-service`。
- 本番化で足す: 永続化 `add-persistence`、認証 `add-auth`、状態 `add-store`、ログ/エラー `add-observability`。
- どの段でも: コードは `coding-standards`、テストは `add-frontend-test`/`add-e2e-test`、UI/API は `verifier-webapp`、
  CI は `setup-ci`、依存は `audit-deps`、節目は `/code-review`、確定したら `push-changes`。

## コーディング規約

> 命名規則・仕様コメント (docstring/TSDoc)・フォーマットの詳細は **`coding-standards` スキル**を参照
> (ruff の `D`/`N`、eslint `naming-convention` で機械強制)。識別子は英語、コメント/docstring は日本語。

### Python (backend)
- ruff (lint + format) を必ず通す
- 型ヒントは必須。`Any` は避ける
- FastAPI ルーターには `response_model` を必ず指定
- 個別ルーターに `/api` prefix を付けない (`main.py` で一括付与)
- 公開クラス/関数には Google スタイルの docstring (日本語) を付ける。仕様に対応する箇所は `由来: REQ-/SPEC-/DD-` を任意で添える

### TypeScript / Vue (frontend)
- Vue は **Composition API + `<script setup lang="ts">`** で統一。Options API は使わない
- Props/Emits は TypeScript の型で定義 (runtime declaration は使わない)
- スタイルは `<style scoped>` または CSS Modules。グローバル CSS を増やさない
- API 通信は `src/services/` に集約。コンポーネントから直接 `fetch` を書かない
- 型/インターフェースは PascalCase、`I` 接頭辞は使わない。公開関数/型に TSDoc (日本語) を付ける

## テスト
- backend は pytest。新規エンドポイントには最低 1 件のテストを書く
- frontend のテストは現状未導入 — 必要になったら Vitest を追加

## 動作確認
UI/API の変更は **必ずブラウザで動作確認** したうえで完了報告する。
型チェック / テストのパスだけで「完了」と言わない。

## やらないこと
- 不要な抽象化や将来の拡張のための足場作り
- 未使用コードや空関数の温存
- requirements.txt との二重管理 (依存は `pyproject.toml` に一元化)
