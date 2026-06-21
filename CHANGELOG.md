# Changelog

このプロジェクトの主要な変更点を記録します。
書式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に準拠し、
バージョニングは [Semantic Versioning](https://semver.org/lang/ja/) に従います。

## [Unreleased]

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

[Unreleased]: https://github.com/itouhi/claude-fullstack-starter/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/itouhi/claude-fullstack-starter/releases/tag/v0.0.1
