# Rulesets（ブランチ保護）の設定方法

**日本語** | [English](rulesets-setup.en.md)

`main` と `sandbox/main` に適用しているブランチ保護を、GitHub の新しい **Rulesets** で設定する手順です。classic branch protection ではなく Rulesets に一本化しています。

## 何を強制するか

| ルール | 設定 |
|---|---|
| Require a pull request | ✅（承認 0） |
| Require status checks | `backend`, `frontend` |
| Strict（base の最新取込必須） | ✅ |
| Block force push（non_fast_forward） | ✅ |
| Block deletion | ✅ |
| Bypass actors | **なし（管理者もバイパス不可）** |

> classic の `enforce_admins: true` 相当は、Rulesets では **bypass_actors を空**にすることで実現します（`current_user_can_bypass: never`）。

## 方法 A: GitHub UI

1. リポジトリの **Settings → Rules → Rulesets → New branch ruleset**。
2. **Ruleset Name** を入力（例: `main`）、**Enforcement status** を `Active`。
3. **Target branches** で対象を指定:
   - `main` 用 … `Include default branch`
   - `sandbox/main` 用 … `Include by pattern` に `sandbox/main`
4. **Rules** で以下を有効化:
   - Restrict deletions
   - Block force pushes
   - Require a pull request before merging（Required approvals = 0）
   - Require status checks to pass → `backend`, `frontend` を追加、**Require branches to be up to date before merging** を ON
5. **Bypass list** は空のまま（管理者も含めバイパス不可）。
6. Create。`sandbox/main` 用にもう 1 つ同様に作成します。

## 方法 B: gh CLI（API）

`main` 用 ruleset（デフォルトブランチ対象）:

```bash
cat > ruleset-main.json <<'JSON'
{
  "name": "main",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "pull_request", "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false,
        "allowed_merge_methods": ["merge", "squash", "rebase"]
    } },
    { "type": "required_status_checks", "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [ { "context": "backend" }, { "context": "frontend" } ]
    } }
  ]
}
JSON

gh api --method POST repos/<owner>/<repo>/rulesets --input ruleset-main.json
```

`sandbox/main` 用 ruleset は、`name` と `conditions` だけ変えて同じ rules を投入します:

```bash
# 上記 JSON の差分のみ
#   "name": "sandbox-main",
#   "conditions": { "ref_name": { "include": ["refs/heads/sandbox/main"], "exclude": [] } }
gh api --method POST repos/<owner>/<repo>/rulesets --input ruleset-sandbox.json
```

## 確認

```bash
# ルールセット一覧
gh api repos/<owner>/<repo>/rulesets --jq '.[] | "\(.id) \(.name) \(.enforcement)"'

# 特定ブランチに効いているルール
gh api repos/<owner>/<repo>/rules/branches/main --jq '[.[].type] | join(", ")'

# 必須チェック / strict
gh api repos/<owner>/<repo>/rules/branches/main \
  --jq '.[] | select(.type=="required_status_checks") | {strict:.parameters.strict_required_status_checks_policy, checks:[.parameters.required_status_checks[].context]}'

# 管理者もバイパス不可か
gh api repos/<owner>/<repo>/rulesets/<id> --jq '.current_user_can_bypass'   # => "never"
```

## 挙動メモ

- CI が失敗している間は PR の `mergeStateStatus = BLOCKED`。`--admin` 強制マージも `Repository rule violations found` で拒否されます。
- 必須チェック名（`backend` / `frontend`）は、ワークフローの **ジョブ名**と一致させる必要があります（`ci.yml` / `sandbox-ci.yml` のジョブ名）。
- `sandbox/main` への PR では `sandbox-ci.yml` が `backend` / `frontend` を生成するため、同じチェック名で保護できます。
- `block-sandbox-pr.yml`（`pull_request_target`）の定義は**デフォルトブランチ（main）**のものが使われます。sandbox の取り込み制御ロジックは main 側に置きます（[development-process.md](development-process.md) 参照）。
