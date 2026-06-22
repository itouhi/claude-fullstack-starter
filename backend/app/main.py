from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.config import settings
from app.store import store


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """起動時に DATABASE_URL があれば DB からデータを読み込む (N-2)。"""
    if settings.database_url:
        from app.db import get_engine, init_db, load_snapshot

        engine = get_engine(settings.database_url)
        init_db(engine)
        load_snapshot(engine, store)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.middleware("http")
async def _persist_after_mutation(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """更新系リクエスト成功後にストアを DB へ書き戻す (DATABASE_URL 設定時)。"""
    response = await call_next(request)
    if (
        settings.database_url
        and request.method in ("POST", "PUT", "PATCH", "DELETE")
        and response.status_code < 400
    ):
        from app.db import get_engine, save_snapshot

        save_snapshot(get_engine(settings.database_url), store)
    return response


@app.get("/health")
def health() -> dict[str, str]:
    """ヘルスチェック。常に `{"status": "ok"}` を返す。"""
    return {"status": "ok"}
