---
name: audit-deps
description: 依存パッケージの脆弱性を監査する (SCA)。npm audit (frontend) と pip-audit (backend) で既知の脆弱性を検出し対応する。「依存監査」「脆弱性チェック」「npm audit」「pip-audit」「SCA」などで起動。
---

# audit-deps

依存パッケージ (直接・推移的) の**既知の脆弱性を監査** (Software Composition Analysis) し、対応する。

> 出典: SCA / 依存スキャンは CI セキュリティの基本。SBOM と併せて既知脆弱性を特定 (wiz.io)。
> OWASP Top 10 の「Supply Chain / Vulnerable Components」に対応。

## 監査コマンド
- **frontend**: `cd frontend && npm audit` (`--audit-level=high` で閾値)。修正は `npm audit fix` (破壊的変更は `--force` を慎重に)。
- **backend**: `pip-audit` (`pip install pip-audit` → `cd backend && pip-audit`)。`pyproject.toml` の依存を検査。

## 手順
1. 両方を実行し、検出された脆弱性を**重大度順**に整理。
2. 対応方針を決める:
   - 直接依存 → 安全なバージョンへ更新 (`package.json` / `pyproject.toml`)。
   - 推移的依存 → 上位依存の更新 or overrides/resolutions。
   - 修正不可 (誤検知・到達不能) → 理由を記録し一時的に許容 (放置しない)。
3. 更新後に `setup-ci` のチェック (ruff/pytest/lint/type-check) が緑であることを確認。
4. 監査を **CI に組み込む** (`setup-ci` の npm audit step。pip-audit も同様に追加可)。

## ガードレール
- 監査は**定期 + 依存追加時**に実施。放置で脆弱性が積み上がらないようにする。
- `npm audit fix --force` はメジャー更新を含みうる。実施後は必ずテスト/動作確認。
- 誤検知・許容は**根拠を残す** (なぜ安全か)。サイレントに無視しない。
- アプリ全体のセキュリティレビューは Claude Code 内蔵の `/security-review` を併用 (本スキルは依存に特化)。
- 関連: `setup-ci` (CI で自動監査)、`add-auth` / `add-observability` (実装面のセキュリティ)。
