# アーキテクチャ / リポジトリ構造

**日本語** | [English](architecture.en.md)

FastAPI (backend) と Vue 3 (frontend) を 1 リポジトリで管理する構成です。開発は VSCode Dev Container 上で行います。

## 技術スタック

| レイヤ | 技術 |
|---|---|
| Backend | FastAPI / Python 3.14 / Pydantic / pytest / ruff |
| Frontend | Vue 3 (Composition API + `<script setup>`) / Vite / TypeScript / ESLint |
| 環境 | VSCode Dev Container (Ubuntu) |
| CI | GitHub Actions (ruff / pytest / eslint / type-check) |

## ディレクトリ構造

```
.
├── .devcontainer/             # Dev Container 設定
├── .claude/skills/            # Claude Code 用プロジェクトスキル
├── .github/workflows/         # CI・ブランチ保護・sandbox CI
│   ├── ci.yml                 # main 用 CI (backend/frontend)
│   ├── sandbox-ci.yml         # sandbox/** 用 CI
│   └── block-sandbox-pr.yml   # sandbox/* -> main の PR を自動クローズ
├── backend/
│   ├── app/
│   │   ├── api/               # ルーター (__init__.py で集約)
│   │   │   └── hello.py
│   │   ├── config.py          # 設定 (BaseSettings)
│   │   └── main.py            # FastAPI エントリポイント
│   ├── tests/                 # pytest
│   └── pyproject.toml         # 依存・ruff 設定 (一元管理)
├── frontend/
│   ├── src/
│   │   ├── services/          # API 通信を集約 (api.ts)
│   │   ├── App.vue
│   │   └── main.ts            # Vue エントリポイント
│   └── package.json
├── docs/                      # 本ドキュメント
├── CLAUDE.md                  # プロジェクト規約 / スキル体系
└── README.md
```

## コンポーネント構成

```mermaid
flowchart TB
    subgraph FE["frontend (Vue 3 + Vite)"]
        direction TB
        app["App.vue<br/>(SFC / Composition API)"]
        svc["services/api.ts<br/>(API 通信を集約)"]
        app --> svc
    end

    subgraph BE["backend (FastAPI)"]
        direction TB
        mainpy["main.py<br/>FastAPI() + CORS"]
        router["api/__init__.py<br/>router 集約"]
        hello["api/hello.py<br/>GET /hello"]
        cfg["config.py<br/>Settings"]
        mainpy --> router --> hello
        mainpy -.読込.-> cfg
    end

    svc -->|"HTTP GET /api/hello"| mainpy

    classDef fe fill:#e7f0ff,stroke:#4a78c8;
    classDef be fill:#e9f7e9,stroke:#4aa84a;
    class app,svc fe;
    class mainpy,router,hello,cfg be;
```

### 設計ルール (CLAUDE.md より)

- **backend**: ルーターに `/api` prefix を付けない (`main.py` で一括付与)。全ルーターに `response_model` を指定。型ヒント必須。
- **frontend**: API 通信は `src/services/` に集約し、コンポーネントから直接 `fetch` しない。Composition API + `<script setup lang="ts">` で統一。

## リクエストの流れ

開発時は Vite の dev server (5173) が `/api/*` を backend (8000) にプロキシします。

```mermaid
sequenceDiagram
    participant U as ブラウザ
    participant V as Vite dev server :5173
    participant F as FastAPI :8000
    participant R as api/hello.py

    U->>V: GET / (Vue アプリ)
    V-->>U: index.html + JS
    Note over U: App.vue onMounted で load()
    U->>V: GET /api/hello?name=world
    V->>F: proxy 転送
    F->>R: ルーティング (/api + /hello)
    R-->>F: HelloResponse{ message }
    F-->>V: 200 JSON
    V-->>U: { "message": "Hello, world!" }
```

- フロントは必ず `services/api.ts` の `fetchHello()` を経由します。
- backend は `/api` prefix (`main.py`) + ルーター側の `/hello` で `GET /api/hello` を提供します。
- `/health` はヘルスチェック用エンドポイントです。

## 起動方法 (概要)

```bash
# backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0
# frontend (別ターミナル)
cd frontend && npm run dev -- --host
```

詳細はリポジトリ直下の [README.md](../README.md) を参照してください。
