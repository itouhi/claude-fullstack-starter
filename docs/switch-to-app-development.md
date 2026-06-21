# テンプレートからアプリ開発リポジトリへの移行

**日本語** | [English](switch-to-app-development.en.md)

このリポジトリは「**開発環境そのものを提供するテンプレート**」です。`Use this template` / fork して**実アプリを開発するリポジトリに転換**する場合、テンプレート保守専用の仕組みは不要になります。本書はその撤去対象と手順をまとめます。

> 判断軸: このリポジトリを今後も**テンプレートとして保守する**なら撤去不要。**実アプリ開発に振り切る**なら以下を撤去すると軽くなります。

## 概要: 残すもの / 撤去するもの

| 対象 | アプリ開発での要否 | 理由 |
|---|---|---|
| `ci.yml` | ✅ 残す（中核） | アプリの品質ゲート（lint / test / build） |
| `release.yml` | ✅ 残す | タグ駆動の GitHub Release。アプリのリリースにも有用 |
| CodeQL（default setup） | ✅ 残す | 実アプリではセキュリティ重要度が上がる |
| `freshness.yml` | △ 任意撤去 | 放置期間中の依存ドリフト検知用。能動開発中は毎 PR の CI + dependabot で代替でき価値が薄い |
| `devcontainer-ci.yml` | △ 任意撤去 | devcontainer を頻繁に変えないなら価値が限定的 |
| `docs-skills-ci.yml`（+ `check_docs_skills.py`） | ⚠️ 撤去推奨 | スキル frontmatter / CLAUDE.md 整合 / 日英ペアの検証＝テンプレ構造の維持用 |
| **sandbox 一式** | ⚠️ 撤去推奨 | 下記参照 |

### sandbox 一式とは

`sandbox-ci.yml` ・ `block-sandbox-pr.yml` ・ `sandbox/main` ブランチ ・ `sandbox-main` Ruleset の総称。**CI/Ruleset/スキルなど開発環境自体の変更を `main` に触れず試す**ための装置（[development-process.md](./development-process.md) の §4）。アプリ開発では通常のフィーチャーブランチ運用で足りるため、まるごと不要になりやすい。

## 撤去手順

各撤去は**関心事ごとに PR を分ける**ことを推奨（`docs/development-process.md` のフローに従う）。`<owner>/<repo>` は自分のリポジトリに読み替える。

### 1. sandbox 一式の撤去

```bash
# 1-1. sandbox/main の Ruleset を確認し削除
gh api repos/<owner>/<repo>/rulesets --jq '.[] | "\(.id) \(.name)"'
gh api --method DELETE repos/<owner>/<repo>/rulesets/<sandbox-main の id>

# 1-2. sandbox/main ブランチを削除（Ruleset 削除後でないと保護で拒否される）
git push origin --delete sandbox/main

# 1-3. ワークフローを削除
git rm .github/workflows/sandbox-ci.yml .github/workflows/block-sandbox-pr.yml
```

- ドキュメント側も整理: `docs/development-process.md`（§ブランチ戦略・CI・sandbox）、`docs/rulesets-setup.md`（`sandbox/main` 用 Ruleset）、`CONTRIBUTING.md`・`README.md` / `README.en.md` の sandbox 記述を削除。
- `.github/pull_request_template.md` の sandbox 注意書きも削除。

### 2. docs/skills 整合 CI の撤去

```bash
git rm .github/workflows/docs-skills-ci.yml .github/scripts/check_docs_skills.py
```

- スキルの保守を続けないなら `.claude/skills/` 自体の要否も検討（残してもよい）。

### 3. freshness CI の撤去（任意）

```bash
git rm .github/workflows/freshness.yml
# 自動起票ラベルが不要なら
gh label delete freshness-failure --yes
```

### 4. devcontainer CI の撤去（任意）

```bash
git rm .github/workflows/devcontainer-ci.yml
```

## 撤去後の確認

- **必須ステータスチェック名（`backend` / `frontend`）は `ci.yml` が供給し続ける**ため、`main` の Ruleset は変更不要（壊さないこと）。
- 残る GitHub Actions: `ci.yml` / `release.yml`（+ CodeQL）。
- 残るブランチ運用: `main` + フィーチャーブランチ（トランクベース）。
- 各撤去 PR が CI 緑でマージできることを確認。

## 撤去後の最小構成（イメージ）

```
.github/workflows/
├── ci.yml        # backend / frontend の品質ゲート
└── release.yml   # v* タグ → GitHub Release
（+ CodeQL: GitHub default setup）
```

> 迷ったら段階的に。まず sandbox 一式 → docs-skills → freshness → devcontainer の順で、各 PR を分けて撤去すると影響を確認しながら進められます。
