---
name: setup-ci
description: GitHub Actions の CI を整備・更新する。backend (ruff/pytest) と frontend (lint/type-check) の品質チェックと依存監査を PR で自動実行する。「CI を作る」「GitHub Actions」「自動テスト」「lint を CI で」などで起動。
---

# setup-ci

手動で回している品質チェック (ruff / pytest / lint / type-check) を **GitHub Actions で自動化**する。
PR・main への push で実行し、緑でないとマージしない運用にする。

> 出典: CI/CD testing strategies (circleci.com), CI/CD security scanning / SCA (wiz.io)。

## 同梱ワークフロー
`.github/workflows/ci.yml` を配置済み。ジョブ:
- **backend**: `pip install -e ".[dev]"` → `ruff check .` → `ruff format --check .` → `pytest -q`
- **frontend**: `npm ci` → `npm run lint` → `npm run type-check` → `npm audit` (依存監査・非ブロック)

## 手順 (拡張・更新するとき)
1. チェックを足すなら該当ジョブに step を追加 (例 backend に `mypy app`、frontend に E2E)。
2. ローカルで**同じコマンドが緑**になることを先に確認してから CI に入れる (赤い CI を放置しない)。
3. 重い/外部依存のステップ (E2E, デプロイ) はジョブを分け、必要なら `needs:` で順序付け。
4. 依存監査 (`npm audit` / `pip-audit`) は誤検知・推移的脆弱性で赤くなりがち。**まずは report のみ (continue-on-error)** にし、方針が固まったら `--audit-level` で段階的に厳格化する。監査の運用・対応方針は `audit-deps` スキルに従う。

## ガードレール
- CI のコマンドは**ローカルの開発コマンドと一致**させる (CLAUDE.md / coding-standards の ruff・eslint と同じ)。乖離させない。
- シークレットはワークフローにハードコードしない。`secrets` を使う。
- ブランチ保護で「CI 必須」にするのは運用判断 (本リポジトリは sandbox 例外あり)。
- 関連: `coding-standards` (ローカルと同じ lint)、`add-frontend-test` (CI に Vitest 追加)、`add-e2e-test`。
