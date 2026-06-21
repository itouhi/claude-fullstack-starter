# Architecture / repository structure

[日本語](architecture.md) | **English**

FastAPI (backend) and Vue 3 (frontend) live in a single repository. Development happens inside a VSCode Dev Container.

## Tech stack

| Layer | Tech |
|---|---|
| Backend | FastAPI / Python 3.14 / Pydantic / pytest / ruff |
| Frontend | Vue 3 (Composition API + `<script setup>`) / Vite / TypeScript / ESLint |
| Environment | VSCode Dev Container (Ubuntu) |
| CI | GitHub Actions (ruff / pytest / eslint / type-check) |

## Directory structure

```
.
├── .devcontainer/             # Dev Container config
├── .claude/skills/            # Claude Code project skills
├── .github/workflows/         # CI / branch protection / sandbox CI
│   ├── ci.yml                 # CI for main (backend/frontend)
│   ├── sandbox-ci.yml         # CI for sandbox/**
│   └── block-sandbox-pr.yml   # auto-close sandbox/* -> main PRs
├── backend/
│   ├── app/
│   │   ├── api/               # routers (aggregated in __init__.py)
│   │   │   └── hello.py
│   │   ├── config.py          # settings (BaseSettings)
│   │   └── main.py            # FastAPI entry point
│   ├── tests/                 # pytest
│   └── pyproject.toml         # deps & ruff config (single source)
├── frontend/
│   ├── src/
│   │   ├── services/          # API calls centralized (api.ts)
│   │   ├── App.vue
│   │   └── main.ts            # Vue entry point
│   └── package.json
├── docs/                      # this documentation
├── CLAUDE.md                  # project conventions / skill system
└── README.md
```

## Component layout

```mermaid
flowchart TB
    subgraph FE["frontend (Vue 3 + Vite)"]
        direction TB
        app["App.vue<br/>(SFC / Composition API)"]
        svc["services/api.ts<br/>(centralized API calls)"]
        app --> svc
    end

    subgraph BE["backend (FastAPI)"]
        direction TB
        mainpy["main.py<br/>FastAPI() + CORS"]
        router["api/__init__.py<br/>router aggregation"]
        hello["api/hello.py<br/>GET /hello"]
        cfg["config.py<br/>Settings"]
        mainpy --> router --> hello
        mainpy -.reads.-> cfg
    end

    svc -->|"HTTP GET /api/hello"| mainpy

    classDef fe fill:#e7f0ff,stroke:#4a78c8;
    classDef be fill:#e9f7e9,stroke:#4aa84a;
    class app,svc fe;
    class mainpy,router,hello,cfg be;
```

### Design rules (from CLAUDE.md)

- **backend**: Routers do not add the `/api` prefix (applied centrally in `main.py`). Every router specifies `response_model`. Type hints are required.
- **frontend**: API calls are centralized in `src/services/`; components never call `fetch` directly. Use Composition API + `<script setup lang="ts">` consistently.

## Request flow

During development the Vite dev server (5173) proxies `/api/*` to the backend (8000).

```mermaid
sequenceDiagram
    participant U as Browser
    participant V as Vite dev server :5173
    participant F as FastAPI :8000
    participant R as api/hello.py

    U->>V: GET / (Vue app)
    V-->>U: index.html + JS
    Note over U: App.vue calls load() in onMounted
    U->>V: GET /api/hello?name=world
    V->>F: proxy forward
    F->>R: routing (/api + /hello)
    R-->>F: HelloResponse{ message }
    F-->>V: 200 JSON
    V-->>U: { "message": "Hello, world!" }
```

- The frontend always goes through `fetchHello()` in `services/api.ts`.
- The backend serves `GET /api/hello` via the `/api` prefix (`main.py`) plus the router's `/hello`.
- `/health` is a health-check endpoint.

## Running (overview)

```bash
# backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0
# frontend (separate terminal)
cd frontend && npm run dev -- --host
```

See the repository-root [README.en.md](../README.en.md) for details.
