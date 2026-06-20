# claude-fullstack-starter

**日本語** | [English](README.en.md)

[![CI](https://github.com/itouhi/claude-fullstack-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/itouhi/claude-fullstack-starter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

FastAPI (Python 3.12) + Vue 3 + Vite + TypeScript のフルスタック開発テンプレート。
VSCode Dev Container、GitHub Actions による CI、ブランチ保護 (Rulesets)、Claude Code 用スキルと開発プロセスドキュメントを同梱しています。

![概要イメージ図](docs/images/overview-diagram.svg)

> 構造とプロセスの詳細は [`docs/`](docs/README.md) を参照（[architecture](docs/architecture.md) / [development-process](docs/development-process.md)）。

## 特徴

- **Backend**: FastAPI / Pydantic / pytest / ruff
- **Frontend**: Vue 3（Composition API + `<script setup lang="ts">`）/ Vite / TypeScript / ESLint
- **環境**: VSCode Dev Container ですぐ起動できる
- **CI**: PR ごとに backend / frontend の品質チェックを自動実行
- **ブランチ保護**: Rulesets で「CI が緑のときだけ `main` にマージ」を強制
- **Claude Code スキル**: API/コンポーネント追加から文書化・CI まで雛形化

## ディレクトリ構成

```
.
├── .devcontainer/        # VSCode Dev Container 設定
├── .claude/skills/       # Claude Code 用プロジェクトスキル
├── .github/workflows/    # CI・ブランチ保護・sandbox CI
├── docs/                 # 構造・開発プロセスの図解資料
├── backend/              # FastAPI アプリケーション
│   ├── app/
│   │   ├── api/          # ルーター (__init__.py で集約)
│   │   ├── config.py
│   │   └── main.py
│   ├── tests/
│   └── pyproject.toml
└── frontend/             # Vue 3 + Vite + TS
    ├── src/
    │   ├── services/     # API 通信を集約
    │   ├── App.vue
    │   └── main.ts
    └── package.json
```

## このテンプレートを使う

```bash
# クローンして自分のプロジェクトとして使い始める
git clone https://github.com/itouhi/claude-fullstack-starter.git myapp
cd myapp
rm -rf .git && git init -b main && git add -A && git commit -m "Initial commit"

# 自分の GitHub リポジトリへ公開 (gh CLI は dev container に同梱)
gh repo create <your-account>/myapp --private --source=. --remote=origin --push
```

## 開始手順

### 1. Dev Container を開く

VSCode で本リポジトリを開き、コマンドパレットから **「Dev Containers: Reopen in Container」** を実行。
`.devcontainer/post-create.sh` が backend の venv 作成 + 依存インストール、frontend の `npm install` を自動で行う。

### 2. backend を起動

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0
```

`http://localhost:8000/docs` で Swagger UI を確認できる。

### 3. frontend を起動 (別ターミナル)

```bash
cd frontend
npm run dev -- --host
```

`http://localhost:5173` を開く。`/api/*` は Vite proxy 経由で backend (8000) に転送される。

## 開発コマンド

### backend
```bash
pytest -q              # テスト
ruff check .           # lint
ruff format .          # format
```

### frontend
```bash
npm run dev            # 開発サーバー
npm run build          # 本番ビルド
npm run type-check     # 型チェック
npm run lint           # ESLint
npm run format         # Prettier
```

## Claude Code スキル

`.claude/skills/` に以下のプロジェクト固有スキルが用意されている:

- **add-api-endpoint** — FastAPI のエンドポイントを雛形ごと追加
- **add-vue-component** — Vue 3 SFC を Composition API + TS で追加
- **add-fullstack-feature** — backend → frontend service → component を一気通貫で追加
- **write-dev-docs** — 開発工程ドキュメント (要求事項〜リリース) を `docs/<機能名>/` に作成
- **push-changes** — 変更を関心事ごとにコミット分割し、まとめてブランチへ push
- **run-dev-cycle** — 機能を開発工程に沿って半自動で回す (文書化+実装+テストのオーケストレーション)
- **verifier-webapp** — UI/API を実ブラウザ (Playwright) で動作確認
- **coding-standards** — 命名規則・仕様コメント・フォーマットの規約 (ruff D / eslint naming で機械強制)
- **compose-service** — 複数機能をマニフェストで束ね1サービス (vue-router App Shell + BFF集約) に組み立てる
- **setup-ci** — GitHub Actions で品質チェックと依存監査を自動化
- **add-persistence** — in-memory を実 DB 化 (SQLModel + Alembic マイグレーション)
- **add-frontend-test** — frontend に Vitest + Testing Library で単体テストを導入
- **add-auth** — JWT + RBAC の本格認証・認可
- **add-store** — frontend の状態管理 (Pinia)
- **add-observability** — 構造化ログ・本番安全なエラーハンドリング・メトリクス
- **add-e2e-test** — Playwright の自動 E2E (回帰テスト)
- **audit-deps** — 依存脆弱性監査 (npm audit / pip-audit)

詳細は各 `SKILL.md` および [CLAUDE.md](CLAUDE.md) を参照。

## ブランチ運用 & 品質ゲート

- `main` (リリース) / `dev` (統合) を基点に、`feat/*` `fix/*` `docs/*` `ci/*` の作業ブランチを切って PR を出す。
- `main` は **Rulesets で保護**: PR 必須 + CI (`backend` / `frontend`) 必須 + strict (最新取込)、bypass なし (管理者もマージ不可)。**CI が緑のときだけマージできる。**
- **CI ワークフロー** (`.github/workflows/`):
  - `ci.yml` — `main` / `dev` の品質チェック
  - `sandbox-ci.yml` — `sandbox/**` の検証用 CI
  - `block-sandbox-pr.yml` — `sandbox/*` → `main` / `dev` の PR を自動クローズ (誤マージ防止)。`sandbox/**` → `sandbox/main` は許可
- `sandbox/main` は `main` をミラーした sandbox 検証の基点で、`main` と同等の保護を適用。`sandbox/<名前>` で使い捨ての検証ブランチを切って、本番に触れず保護挙動を試せる。

詳細は [docs/development-process.md](docs/development-process.md) を参照。

## ライセンス

[MIT License](LICENSE) で公開しています。

本リポジトリの内容は [Claude Code](https://www.anthropic.com/claude-code) を併用して作成しています。
