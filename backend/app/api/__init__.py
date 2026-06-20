from fastapi import APIRouter

from app.api import hello

router = APIRouter()
router.include_router(hello.router, tags=["hello"])
