---
name: add-persistence
description: in-memory データを実 DB に置き換える。SQLModel/SQLAlchemy + Alembic マイグレーション、セッション依存性注入、リポジトリ分離を導入する。「DB 化」「永続化」「マイグレーション」「SQLModel」などで起動。
---

# add-persistence

機能の in-memory ストア (`_USERS` 等) を **実データベース**に置き換える。

> 出典: FastAPI in prod — DB migrations / async DB (propelauth.com, render.com)。
> 方針: スキーマ変更は**マイグレーションで管理** (アプリ起動時の自動 create に頼らない)。

## 導入するもの
- **SQLModel** (SQLAlchemy + Pydantic) または SQLAlchemy 2.0。
- **Alembic** によるマイグレーション。
- DB セッションを **依存性注入** (`Depends(get_session)`) で渡す。
- データアクセスを**リポジトリ/CRUD 層**に分離し、ルーターは薄く保つ。

## 手順
1. 依存追加: `pyproject.toml` に `sqlmodel`, `alembic`, DB ドライバ (`psycopg[binary]` / 開発は `sqlite`)。
2. `app/db.py`: engine と `get_session()` を定義 (接続情報は `Settings` から)。
3. モデル定義: `<Resource>` を `SQLModel, table=True` で定義 (API の `<Resource>Response` とは分離 or 兼用を明示)。
4. **Alembic 初期化**: `alembic init`、`env.py` で metadata を読み、`alembic revision --autogenerate -m "..."` → `alembic upgrade head`。
5. ルーターを書き換え: `_USERS` 直参照 → `session.exec(select(User))` 等。`Depends(get_session)` を注入。
6. テスト: テスト用 DB (sqlite in-memory or 一時ファイル) を fixture で用意し、各テストでロールバック/初期化。
7. `verifier-webapp` で API/UI が DB 経由でも動くことを実機確認。

## ガードレール
- スキーマ変更は必ず**マイグレーションファイル**を作る。本番の自動 `create_all` に依存しない。
- N+1 を避ける (必要に応じ eager load)。重い処理は async / 適切なインデックス。
- 接続情報・認証情報は `.env` / secrets。コミットしない。
- 命名・docstring は `coding-standards`。新規エンドポイントは `add-api-endpoint` の規約 (response_model 等) を踏襲。
- DB セッションはリクエストスコープ。グローバル共有しない。
