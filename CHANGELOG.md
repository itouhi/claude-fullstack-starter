# Changelog

このプロジェクトの主要な変更点を記録します。
書式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に準拠し、
バージョニングは [Semantic Versioning](https://semver.org/lang/ja/) に従います。

## [Unreleased]

## [0.0.2] - 2026-06-21

開発環境（このリポジトリの成果物）の保守体制を整備したリリース。CI を 2 系統追加し、
ブランチ戦略をトランクベースに統一、sandbox 検証環境を開通した。

### Added

- **devcontainer CI** (`devcontainer-ci.yml`): devcontainer をコールドビルドし、`post-create.sh` 実行後に backend / frontend / Claude CLI のスモークを回す
- **docs/skills CI** (`docs-skills-ci.yml` + `check_docs_skills.py`): スキル frontmatter・CLAUDE.md との整合・日英ペア・内部リンク切れを検証
- **週次 freshness CI** (`freshness.yml`): 依存ドリフトと外部リンク腐りをクリーン環境で能動検知し、失敗時に issue を自動起票（非ブロッキング）
- **frontend build ゲート**: `ci.yml` / `sandbox-ci.yml` の frontend ジョブで `npm run build` を実行し、本番ビルドの破損を検出
- **sandbox 検証環境**: `sandbox/main`（main 同等の Ruleset）を基点に、本番 `main` に触れず CI/Ruleset/skill を検証できる導線を整備

### Changed

- **ブランチ戦略をトランクベースに統一**: 実体の無い `dev` 統合ブランチへの参照を CI・docs から削除
- 全 GitHub Actions ワークフローに最小権限 (`permissions: contents: read`) を設定（CodeQL `missing-workflow-permissions` を解消）
- `CLAUDE.md` に貢献フロー（CONTRIBUTING / development-process）への導線を追加

### Fixed

- devcontainer の Python インタープリタパスがフォルダ名固定（`/workspaces/develop`）で実体と不整合だった問題を `${containerWorkspaceFolder}` で修正
- TypeScript 6 の `baseUrl` 非推奨により `npm run build`（`vue-tsc -b`）が失敗していた問題を `paths` の相対化で修正

## [0.0.1] - 2026-06-21

最初のリリース。FastAPI + Vue 3 のフルスタック開発テンプレート一式。

### Added

- **Backend**: FastAPI (Python 3.14) / Pydantic / pytest / ruff によるサンプル API (`/health`, `/api/hello`)
- **Frontend**: Vue 3 (Composition API + `<script setup lang="ts">`) / Vite / TypeScript / ESLint
- **開発環境**: VSCode Dev Container (Node 24 / Python 3.14) ですぐ起動できる構成
- **CI**: GitHub Actions で PR ごとに backend (ruff / pytest) と frontend (lint / type-check) を自動チェック
- **リリース**: `v*` タグ push で自動リリースノート付き GitHub Release を作成するワークフロー
- **ブランチ保護 / sandbox CI**: Rulesets 連携と sandbox ブランチ向け CI
- **Claude Code スキル**: API/コンポーネント追加から文書化・CI・依存監査までの雛形
- **ドキュメント**: README (日本語/英語)、architecture、development-process、各種コミュニティファイル
  (LICENSE / CONTRIBUTING / CODE_OF_CONDUCT / SECURITY / Issue・PR テンプレート / CODEOWNERS)

### Changed

- ツールチェーンを最新化: Node 20 → 24、Python 3.12 → 3.14
- 主要依存を更新: TypeScript 6、Vite 8、`@vitejs/plugin-vue` 6、pydantic / pytest / mypy / setuptools ほか

[Unreleased]: https://github.com/itouhi/claude-fullstack-starter/compare/v0.0.2...HEAD
[0.0.2]: https://github.com/itouhi/claude-fullstack-starter/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/itouhi/claude-fullstack-starter/releases/tag/v0.0.1
