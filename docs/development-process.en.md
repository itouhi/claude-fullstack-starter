# Development process

[日本語](development-process.md) | **English**

This document covers the skill-based implementation flow combined with CI, branch protection (Rulesets), and the sandbox verification environment.

## 1. Branch strategy

| Branch | Role | Protection |
|---|---|---|
| `main` | Release target. Always green | ✅ Ruleset (PR required + CI required) |
| `dev` | Integration branch | CI target (push/PR) |
| `feat/*` `fix/*` `docs/*` `ci/*` | Per feature/fix work branches | PR into main/dev |
| `sandbox/main` | Base for sandbox verification (mirror of main) | ✅ Ruleset (same as main) |
| `sandbox/<name>` | Throwaway verification branch | — |

```mermaid
gitGraph
    commit id: "init"
    branch dev
    branch feature
    commit id: "feat"
    commit id: "test"
    checkout main
    merge feature tag: "PR + CI green"
```

> Cut `feature` off `main`, implement, and merge into `main` once CI is green. `dev` is the integration branch; promotion into `main` always goes through a PR.

> **Naming constraint**: Due to git's ref rules, a plain `sandbox` branch and `sandbox/*` cannot coexist. Therefore all sandbox branches use the `sandbox/<name>` hierarchy.

## 2. CI workflows

Three workflows divide the responsibilities.

```mermaid
flowchart TB
    subgraph wf[".github/workflows"]
        ci["ci.yml<br/>trigger: push/PR → main, dev"]
        sci["sandbox-ci.yml<br/>trigger: push/PR → sandbox/**"]
        blk["block-sandbox-pr.yml<br/>trigger: pull_request_target"]
    end

    ci --> jobs1["backend (ruff/pytest)<br/>frontend (eslint/type-check/test)"]
    sci --> jobs2["backend / frontend<br/>(runs, not skipped, for sandbox/*)"]
    blk --> close["auto-close + comment PRs where<br/>head=sandbox/* and base≠sandbox/*"]
```

- **`ci.yml`** — For `main` / `dev`. Runs `backend` and `frontend` quality checks. Vitest uses `npm run test --if-present`, so branches without tests do not fail.
- **`sandbox-ci.yml`** — For `sandbox/**`. The main CI skips sandbox, so this runs CI in sandbox environments too. It also lives on `main`, so sandbox branches cut from main inherit it.
- **`block-sandbox-pr.yml`** — Prevents merging sandbox branches.

> **Important behavior**: A `pull_request_target` workflow definition is taken from the **default branch (main)**. So the logic that controls sandbox→main must live on `main`.

## 3. Branch protection (Rulesets)

Protection is consolidated into the **modern Rulesets** instead of classic branch protection. The same rules apply to `main` and `sandbox/main`.

| Rule | Setting |
|---|---|
| Require a pull request | ✅ (0 approvals) |
| Require status checks | `backend`, `frontend` |
| Strict (must be up to date) | ✅ |
| Block force push / deletion | ✅ |
| Bypass actors | **none (admins cannot bypass either)** |

```mermaid
flowchart LR
    pr["Open a PR"] --> run["Run CI<br/>backend / frontend"]
    run -->|"either fails"| blocked["BLOCKED<br/>cannot merge (even admins)"]
    run -->|"both pass"| clean["CLEAN"]
    clean --> merge["mergeable"]
    blocked -.push a fix.-> run
```

- While CI is failing, `mergeStateStatus = BLOCKED`, and even `--admin` force-merge is rejected with `Repository rule violations found`.
- Once CI turns green it becomes `CLEAN` and can be merged.

## 4. Sandbox verification environment

This lets you try changes to `main`'s protection or workflows **without touching production main**. Because `sandbox/main` has the same Ruleset as main, it reproduces the protection behavior exactly.

```mermaid
flowchart TB
    m["main (production)"] -->|mirror| sm["sandbox/main<br/>(protection: same as main)"]
    sm -->|branch off| sx["sandbox/feature-x"]
    sx -->|"PR (base=sandbox/main)"| check{"block-sandbox-pr"}
    check -->|"base is sandbox/* → allowed"| sci["verify with Sandbox CI"]
    sci -->|green| mergeok["mergeable into sandbox/main"]

    sx2["sandbox/feature-x"] -->|"PR (base=main)"| check2{"block-sandbox-pr"}
    check2 -->|"base≠sandbox/* → auto-close"| closed["closed"]
```

- PRs `sandbox/** → sandbox/main` are **allowed** (for verification).
- PRs `sandbox/* → main` / `→ dev` are **auto-closed** (to prevent accidental merges).

## 5. Skill-based development flow

Use the skills defined in `CLAUDE.md` to move from requirements to release in stages.

```mermaid
flowchart LR
    doc["write-dev-docs<br/>process docs"] --> build["add-* <br/>implement (API/Vue/fullstack)"]
    build --> test["add-frontend-test / add-e2e-test<br/>verifier-webapp"]
    test --> review["/code-review"]
    review --> push["push-changes<br/>(per-concern commits)"]
    push --> ci2["CI + Rulesets"]
    ci2 --> mainb["main"]

    cross["cross-cutting: coding-standards / setup-ci / audit-deps"] -.- build
    base["foundation: add-persistence / add-auth / add-store / add-observability"] -.- build
```

- **build** (one feature) — `add-api-endpoint` / `add-vue-component` / `add-fullstack-feature`
- **drive through** — `run-dev-cycle` runs requirements→tests as gated doc→build→review→verify→push
- **make a service** — `compose-service` bundles features into an App Shell + BFF
- **cross-cutting / foundation** — `coding-standards`・`setup-ci`・`audit-deps` / `add-persistence`・`add-auth`・`add-store`・`add-observability`

See [CLAUDE.md](../CLAUDE.md) for the full skill system.

## 6. Typical workflow

```mermaid
sequenceDiagram
    participant D as Developer
    participant B as feat/* branch
    participant G as GitHub Actions
    participant M as main (Ruleset)

    D->>B: commit implementation
    D->>M: open PR (base=main)
    M->>G: run ci.yml (backend/frontend)
    alt CI green
        G-->>M: checks pass → CLEAN
        D->>M: squash merge
    else CI fails
        G-->>M: BLOCKED (not even admins)
        D->>B: push a fix
    end
```

1. Cut a work branch off `main` / `dev` (do not use the `sandbox/` prefix).
2. Implement and commit per concern with `push-changes`.
3. Open a PR → cannot merge until CI (`backend` / `frontend`) is green.
4. Merge once green. The Ruleset enforces PR + required CI for `main`.
