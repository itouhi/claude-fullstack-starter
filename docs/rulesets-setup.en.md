# Configuring Rulesets (branch protection)

[日本語](rulesets-setup.md) | **English**

How to set up the branch protection applied to `main` and `sandbox/main` using GitHub's modern **Rulesets**. Protection is consolidated into Rulesets rather than classic branch protection.

## What it enforces

| Rule | Setting |
|---|---|
| Require a pull request | ✅ (0 approvals) |
| Require status checks | `backend`, `frontend` |
| Strict (must be up to date) | ✅ |
| Block force push (non_fast_forward) | ✅ |
| Block deletion | ✅ |
| Bypass actors | **none (admins cannot bypass)** |

> The classic `enforce_admins: true` equivalent is achieved in Rulesets by leaving **bypass_actors empty** (`current_user_can_bypass: never`).

## Method A: GitHub UI

1. Go to **Settings → Rules → Rulesets → New branch ruleset**.
2. Enter a **Ruleset Name** (e.g. `main`) and set **Enforcement status** to `Active`.
3. Choose **Target branches**:
   - For `main` … `Include default branch`
   - For `sandbox/main` … `Include by pattern` with `sandbox/main`
4. Enable these **Rules**:
   - Restrict deletions
   - Block force pushes
   - Require a pull request before merging (Required approvals = 0)
   - Require status checks to pass → add `backend`, `frontend`, and turn ON **Require branches to be up to date before merging**
5. Leave the **Bypass list** empty (no one, including admins, can bypass).
6. Create. Create a second ruleset the same way for `sandbox/main`.

## Method B: gh CLI (API)

Ruleset for `main` (targets the default branch):

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

For the `sandbox/main` ruleset, reuse the same rules and only change `name` and `conditions`:

```bash
# only the diff from the JSON above
#   "name": "sandbox-main",
#   "conditions": { "ref_name": { "include": ["refs/heads/sandbox/main"], "exclude": [] } }
gh api --method POST repos/<owner>/<repo>/rulesets --input ruleset-sandbox.json
```

## Verify

```bash
# list rulesets
gh api repos/<owner>/<repo>/rulesets --jq '.[] | "\(.id) \(.name) \(.enforcement)"'

# rules effective on a branch
gh api repos/<owner>/<repo>/rules/branches/main --jq '[.[].type] | join(", ")'

# required checks / strict
gh api repos/<owner>/<repo>/rules/branches/main \
  --jq '.[] | select(.type=="required_status_checks") | {strict:.parameters.strict_required_status_checks_policy, checks:[.parameters.required_status_checks[].context]}'

# admins cannot bypass
gh api repos/<owner>/<repo>/rulesets/<id> --jq '.current_user_can_bypass'   # => "never"
```

## Behavior notes

- While CI fails, the PR's `mergeStateStatus = BLOCKED`. Even `--admin` force-merge is rejected with `Repository rule violations found`.
- Required check names (`backend` / `frontend`) must match the workflow **job names** (`ci.yml` / `sandbox-ci.yml`).
- For PRs into `sandbox/main`, `sandbox-ci.yml` produces `backend` / `frontend`, so the same check names protect it.
- A `block-sandbox-pr.yml` (`pull_request_target`) definition is taken from the **default branch (main)**, so sandbox gating logic must live on main (see [development-process.en.md](development-process.en.md)).
