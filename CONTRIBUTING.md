# コントリビューションガイド

このプロジェクトへの貢献を歓迎します。以下のルールに沿って進めてください。

## 開発の前提

- 開発は VSCode Dev Container 上で行います（[README](README.md) の開始手順を参照）。
- コーディング規約・ブランチ運用・CI は [`docs/`](docs/README.md) に図解があります。

## ブランチ運用

- `main`（リリース）から **`feat/*` `fix/*` `docs/*` `ci/*`** などの作業ブランチを切ります。
- **`sandbox/` 接頭辞は使わないでください。** `sandbox/*` を head とし `main` を base とする PR は CI（`block-sandbox-pr.yml`）が**自動クローズ**します（sandbox はスキル検証専用）。
- 詳細は [docs/development-process.md](docs/development-process.md) を参照。

## 変更の流れ

1. Issue で課題・提案を共有（任意だが推奨）。
2. 作業ブランチを切って実装。
3. ローカルでチェックを通す:
   ```bash
   # backend
   cd backend && ruff check . && ruff format --check . && pytest -q
   # frontend
   cd frontend && npm run lint && npm run type-check
   ```
4. コミットは **関心事ごとに分割**し、[Conventional Commits](https://www.conventionalcommits.org/) に揃えます（`feat:` `fix:` `docs:` `ci:` `chore:` など）。
5. `main` 向けに PR を作成。

## マージ条件（ブランチ保護）

`main` と `sandbox/main` は **Rulesets** で保護されています。

- **PR 必須**（直接 push 不可）。
- 必須ステータスチェック **`backend` / `frontend`** が緑であること。
- strict（base の最新を取り込み済みであること）。
- バイパス不可（管理者も CI 失敗時はマージできません）。

CI が緑になるまでマージできません。Rulesets の設定方法は [docs/rulesets-setup.md](docs/rulesets-setup.md) を参照してください。

## コーディング規約

- **Python**: 型ヒント必須、`ruff` を通す、公開関数に docstring（日本語）。FastAPI ルーターには `response_model` を指定。
- **TypeScript / Vue**: Composition API + `<script setup lang="ts">`、Props/Emits は型で定義、API 通信は `src/services/` に集約。
- 詳細は `CLAUDE.md` および `coding-standards` スキルを参照。

## ライセンス

コントリビューションは [MIT License](LICENSE) の下で公開されることに同意したものとみなします。
