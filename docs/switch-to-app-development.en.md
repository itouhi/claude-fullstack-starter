# Switching from template to an application repository

[日本語](switch-to-app-development.md) | **English**

This repository is a **template that provides the development environment itself**. When you `Use this template` / fork it to **turn it into a repository for developing a real application**, the template-maintenance-only machinery becomes unnecessary. This document lists what to remove and how.

> Decision axis: if you keep maintaining this as a **template**, no removal is needed. If you commit to **real application development**, removing the items below makes the repo leaner.

## Overview: keep / remove

| Target | Needed for app dev | Reason |
|---|---|---|
| `ci.yml` | ✅ Keep (core) | Quality gate for the app (lint / test / build) |
| `release.yml` | ✅ Keep | Tag-driven GitHub Release; useful for app releases too |
| CodeQL (default setup) | ✅ Keep | Security matters more for a real app |
| `freshness.yml` | △ Optional removal | Detects dependency drift during idle periods; under active development, per-PR CI + dependabot cover it |
| `devcontainer-ci.yml` | △ Optional removal | Limited value unless you change the devcontainer often |
| `docs-skills-ci.yml` (+ `check_docs_skills.py`) | ⚠️ Recommended removal | Validates skill frontmatter / CLAUDE.md consistency / JA-EN parity — i.e. template structure upkeep |
| **sandbox apparatus** | ⚠️ Recommended removal | See below |

### What the sandbox apparatus is

The collective of `sandbox-ci.yml`, `block-sandbox-pr.yml`, the `sandbox/main` branch, and the `sandbox-main` Ruleset. It exists to **try changes to the dev environment itself (CI/Rulesets/skills) without touching `main`** (see §4 of [development-process.en.md](./development-process.en.md)). For app development, ordinary feature branches suffice, so the whole thing tends to become unnecessary.

## Removal procedure

Split each removal into its **own PR by concern** (follow the flow in `docs/development-process.en.md`). Replace `<owner>/<repo>` with your repository.

### 1. Remove the sandbox apparatus

```bash
# 1-1. Find and delete the sandbox/main Ruleset
gh api repos/<owner>/<repo>/rulesets --jq '.[] | "\(.id) \(.name)"'
gh api --method DELETE repos/<owner>/<repo>/rulesets/<sandbox-main id>

# 1-2. Delete the sandbox/main branch (protection blocks this until the Ruleset is gone)
git push origin --delete sandbox/main

# 1-3. Remove the workflows
git rm .github/workflows/sandbox-ci.yml .github/workflows/block-sandbox-pr.yml
```

- Clean up docs too: remove sandbox references in `docs/development-process.en.md` (branch strategy / CI / sandbox sections), `docs/rulesets-setup.en.md` (the `sandbox/main` Ruleset), `CONTRIBUTING.md`, and `README.md` / `README.en.md`.
- Also remove the sandbox note in `.github/pull_request_template.md`.

### 2. Remove the docs/skills consistency CI

```bash
git rm .github/workflows/docs-skills-ci.yml .github/scripts/check_docs_skills.py
```

- If you no longer maintain skills, also consider whether `.claude/skills/` itself is needed (keeping it is fine).

### 3. Remove the freshness CI (optional)

```bash
git rm .github/workflows/freshness.yml
# If the auto-issue label is no longer needed
gh label delete freshness-failure --yes
```

### 4. Remove the devcontainer CI (optional)

```bash
git rm .github/workflows/devcontainer-ci.yml
```

## Post-removal checks

- The **required status check names (`backend` / `frontend`) are still produced by `ci.yml`**, so the `main` Ruleset needs no change (don't break it).
- Remaining GitHub Actions: `ci.yml` / `release.yml` (+ CodeQL).
- Remaining branching: `main` + feature branches (trunk-based).
- Confirm each removal PR can merge with green CI.

## Minimal post-removal layout (illustrative)

```
.github/workflows/
├── ci.yml        # backend / frontend quality gate
└── release.yml   # v* tag -> GitHub Release
(+ CodeQL: GitHub default setup)
```

> When in doubt, go incrementally: remove the sandbox apparatus → docs-skills → freshness → devcontainer, one PR at a time, so you can observe the impact as you go.
