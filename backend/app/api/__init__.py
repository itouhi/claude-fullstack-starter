from fastapi import APIRouter

from app.api import (
    accounts,
    cash_book,
    closing,
    export,
    fixed_assets,
    hello,
    imports,
    journal,
    reports,
    tax,
    vouchers,
    year_end,
)

router = APIRouter()
router.include_router(hello.router, tags=["hello"])
router.include_router(accounts.router, tags=["masters"])
router.include_router(journal.router, tags=["journal"])
router.include_router(cash_book.router, tags=["cash-book"])
router.include_router(imports.router, tags=["imports"])
router.include_router(fixed_assets.router, tags=["fixed-assets"])
router.include_router(reports.router, tags=["reports"])
router.include_router(closing.router, tags=["closing"])
router.include_router(tax.router, tags=["tax"])
router.include_router(vouchers.router, tags=["vouchers"])
router.include_router(export.router, tags=["export"])
router.include_router(year_end.router, tags=["year-end"])
