"""勘定科目・税区分マスタの API (M1 core-masters)。

由来: 要件定義 F-201 / F-204 / 全体基本設計 §5。
"""

from fastapi import APIRouter

from app.domain.accounts import Account, TaxCategory
from app.store import store

router = APIRouter()


@router.get("/accounts", response_model=list[Account])
def list_accounts() -> list[Account]:
    """勘定科目マスタを表示順で返す。

    Returns:
        表示順 (`order`) でソートした勘定科目の一覧。
    """
    return sorted(store.accounts.values(), key=lambda a: a.order)


@router.get("/tax-categories", response_model=list[TaxCategory])
def list_tax_categories() -> list[TaxCategory]:
    """税区分マスタの一覧を返す。

    Returns:
        税区分の一覧 (課税/軽減/非課税/対象外)。
    """
    return list(store.tax_categories.values())
