from fastapi import APIRouter

from app.api import calc, hello

router = APIRouter()
router.include_router(hello.router, tags=["hello"])
router.include_router(calc.router, tags=["calc"])
