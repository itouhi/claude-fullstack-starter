---
name: add-api-endpoint
description: Scaffold a new FastAPI endpoint under backend/app/api/, register it in the router, and add a pytest test. Triggers when the user asks to "add an API", "新しいエンドポイント", "新規API", etc.
---

# add-api-endpoint

新しい FastAPI エンドポイントを追加します。

## 入力として確認すること

1. **リソース名** (例: `users`, `tasks`) — snake_case の単数 or 複数
2. **HTTP method** と **path** (例: `GET /users`, `POST /tasks/{id}`)
3. **リクエスト / レスポンスのスキーマ** — フィールド名と型
4. **永続化の有無** — DB を使うか、メモリのみか (初期は in-memory で OK)

## 手順

1. `backend/app/api/<resource>.py` を作成し、`APIRouter` を定義
2. Pydantic モデル (`<Resource>Request`, `<Resource>Response`) を同ファイル or `backend/app/schemas/` に定義
3. `backend/app/api/__init__.py` の `router.include_router(...)` に新ルーターを追加
4. `backend/tests/test_<resource>.py` を作成。最低限以下のテストを書く:
   - 正常系 (200/201)
   - バリデーションエラー (422)
   - 該当パスのエッジケース (404 や境界値)
5. `cd backend && source .venv/bin/activate && pytest -q` を実行し全テスト pass を確認
6. ランタイム挙動を確認したい場合は **`verifier-webapp` スキル**で実サーバ/実ブラウザ越しに API を観測する

## テンプレート

```python
# backend/app/api/<resource>.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/<resource>", tags=["<resource>"])


class <Resource>Response(BaseModel):
    id: int
    name: str


@router.get("/{item_id}", response_model=<Resource>Response)
def get_<resource>(item_id: int) -> <Resource>Response:
    if item_id < 1:
        raise HTTPException(status_code=404, detail="not found")
    return <Resource>Response(id=item_id, name="example")
```

## ガードレール

- `prefix="/api"` は **個別ルーターには付けない**。`app/main.py` で一括付与済み
- 必ず型ヒントを付け、`response_model` を指定する
- DB を使う場合は依存性注入 (`Depends`) を介す。永続化の導入は `add-persistence` スキル (SQLModel + Alembic) に従う
- 命名・docstring (Googleスタイル)・フォーマットは `coding-standards` スキルに従う (公開関数/クラスは docstring 必須、ruff D で機械強制)
- テストが pass しない状態で完了報告しない
