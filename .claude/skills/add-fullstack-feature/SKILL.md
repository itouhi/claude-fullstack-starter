---
name: add-fullstack-feature
description: Add a full vertical slice — a FastAPI endpoint, a typed frontend service call, and a Vue component that uses it. Use when the user asks for an end-to-end feature like "ユーザー一覧画面を追加" or "新しい機能をフロントとバックに追加".
---

# add-fullstack-feature

バックエンドのエンドポイントから、フロントエンドの API クライアント、Vue コンポーネントまでを一気通貫で追加します。

## 入力として確認すること

1. **機能名** (例: `users-list`, `task-create`)
2. **画面の要件** — 何を表示 / 操作するか
3. **API 仕様** — method / path / リクエスト / レスポンス

## 手順 (順序固定)

### 1. backend
`add-api-endpoint` skill の手順に従う。
- `backend/app/api/<resource>.py` を作成
- `backend/app/api/__init__.py` に登録
- `backend/tests/test_<resource>.py` を作成
- `pytest -q` で pass を確認

### 2. frontend API クライアント
- `frontend/src/services/<resource>.ts` を新規作成 (または既存に追加)
- バックエンドのレスポンス型と一致する TypeScript interface を定義
- `fetch` で `/api/<resource>` を呼ぶ関数を export

```ts
// frontend/src/services/<resource>.ts
export interface <Resource> {
  id: number;
  name: string;
}

export async function list<Resource>(): Promise<<Resource>[]> {
  const res = await fetch("/api/<resource>");
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
```

### 3. frontend コンポーネント
`add-vue-component` skill の手順に従う。
- `frontend/src/components/<Name>.vue` を作成
- `onMounted` で service 関数を呼び、`ref` に格納
- loading / error 状態も持たせる

### 4. 動作確認
- backend を起動: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0`
- frontend を起動: `cd frontend && npm run dev -- --host`
- ブラウザで `http://localhost:5173` を開き、新機能を実際に操作して挙動を確認
- 実ブラウザでの観測（描画・APIステータス・コンソールエラー・スクショ）は `verifier-webapp` スキルで自動化できる

## よく使うパターン (必要な場合のみ)

### 認証 (固定トークン)
ログイン必須の API は、トークンを `Depends` で検証する依存性を挟む。
```python
def require_token(authorization: str | None = Header(default=None)) -> None:
    if authorization != f"Bearer {settings.api_token}":
        raise HTTPException(status_code=401, detail="unauthorized")

@router.get("", response_model=list[UserResponse])
def get_users(_: None = Depends(require_token)) -> list[UserResponse]: ...
```
- backend 設定 (`Settings.api_token`) に既定値を持たせ `.env` で上書き可能にする。
- frontend はトークンを `import.meta.env.VITE_API_TOKEN` から付与し、`frontend/env.d.ts` に型を追加、`frontend/.env.example` を用意する:
  ```ts
  // env.d.ts
  interface ImportMetaEnv { readonly VITE_API_TOKEN: string }
  interface ImportMeta { readonly env: ImportMetaEnv }
  ```
> これは簡易サンプル。本番の認証 (JWT/RBAC/レート制限) は `add-auth` スキルで置き換える。

### in-memory ストア (初期段階)
DB 導入前はモジュールレベルの固定シードで可。
```python
_USERS: list[UserResponse] = [UserResponse(id=1, name="Alice"), ...]
```
> 永続化が必要になったら `add-persistence` スキルで実 DB (SQLModel + Alembic) に置き換える。

### 作成系 (POST + 201 + バリデーション + 採番)
追加 API は `status_code=201`、入力は `Field` 制約で検証 (違反は FastAPI が 422)。in-memory なら id を採番する。
```python
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)  # 空/超過は 422

class TaskResponse(BaseModel):
    id: int
    title: str
    done: bool

_TASKS: list[TaskResponse] = []
_next_id = 1

@router.post("", response_model=TaskResponse, status_code=201)
def create_task(body: TaskCreate) -> TaskResponse:
    global _next_id
    task = TaskResponse(id=_next_id, title=body.title, done=False)
    _TASKS.append(task)
    _next_id += 1
    return task
```
- フロントは `services/` に `createTask(title)` を置き、`POST` + `Content-Type: application/json` + `JSON.stringify` で送る。
- テストは正常系 (201) と 422 (空・超過) を最低含める。in-memory 共有のため **autouse フィクスチャでストアをリセット**して独立性を担保する。

### 前提: vite の `@` エイリアス
`@/services/...` import は `vite.config.ts` の `resolve.alias['@'] = fileURLToPath(new URL('./src', import.meta.url))` が無いと dev サーバが 500 になる。無ければ先に追加する。

## ガードレール

- 必ずこの 3 ステップを **すべて** 終え、ブラウザ動作確認まで行うこと
- 型をバックとフロントで重複定義する場合、名前を揃える (バック: `UserResponse`, フロント: `User`)
- Vite proxy で `/api` は backend (8000) に転送される。フロントから絶対 URL を書かない
- 命名・仕様コメント (docstring/TSDoc)・フォーマットは `coding-standards` スキルに従う (ruff D / eslint naming で機械強制)
- 次の一手 (必要に応じて): 共有状態は `add-store`、永続化は `add-persistence`、本番認証は `add-auth`、テストは `add-frontend-test`/`add-e2e-test`
- 部分的に終わった状態で完了報告しない。途中で中断する場合はどこまで終わったか明示
