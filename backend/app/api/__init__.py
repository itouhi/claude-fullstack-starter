from fastapi import APIRouter

from app.api import accounts, cash_book, hello, journal, reports

router = APIRouter()
router.include_router(hello.router, tags=["hello"])
router.include_router(accounts.router, tags=["masters"])
router.include_router(journal.router, tags=["journal"])
router.include_router(cash_book.router, tags=["cash-book"])
router.include_router(reports.router, tags=["reports"])
