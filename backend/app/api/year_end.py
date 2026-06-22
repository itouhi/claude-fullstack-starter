"""年度繰越の API (M9 data-io)。

期末の資産・負債・純資産残高を翌期首へ繰り越す。損益 (収益・費用) と事業主貸借は
元入金へ振り替え、翌年の期首振替仕訳として計上する (仕訳中心の繰越設計)。

由来: 要件定義 F-904 / P-7 (暦年) / data-io 基本設計 §6。
"""

from datetime import date as date_type

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.journal import persist_entry
from app.api.reports import balance_sheet
from app.domain.accounts import AccountType
from app.domain.journal import JournalEntry, JournalLine, Side
from app.store import store

router = APIRouter()

CAPITAL_ACCOUNT_CODE = "400"  # 元入金 (損益・事業主貸借の振替先)


class BalanceItem(BaseModel):
    """繰越対象の科目残高 (由来: data-io BD-BalanceItem)。"""

    account_code: str
    account_name: str
    account_type: AccountType
    closing_balance: int


class YearEndPreview(BaseModel):
    """年度繰越のドライラン結果 (由来: F-904 / REQ-034)。"""

    fiscal_year: int
    next_fiscal_year: int
    balance_forward: list[BalanceItem]  # 翌期へ繰り越す資産・負債・純資産
    net_income: int  # 当期純利益 (元入金へ振替)
    opening_capital_next: int  # 翌期首の元入金


class CarryForwardResult(BaseModel):
    """年度繰越の実行結果 (由来: F-904)。"""

    fiscal_year: int
    next_fiscal_year: int
    opening_entry: JournalEntry
    opening_capital_next: int


def _build_preview(fiscal_year: int) -> YearEndPreview:
    """貸借対照表から繰越内容を組み立てる (純資産は元入金へ集約)。"""
    bs = balance_sheet(fiscal_year)
    items: list[BalanceItem] = []
    for row, acc_type in (
        *[(r, AccountType.ASSET) for r in bs.assets],
        *[(r, AccountType.LIABILITY) for r in bs.liabilities],
        *[(r, AccountType.EQUITY) for r in bs.equity],
    ):
        items.append(
            BalanceItem(
                account_code=row.account_code,
                account_name=row.account_name,
                account_type=acc_type,
                closing_balance=row.amount,
            )
        )
    # 翌期首の元入金 = 資産合計 − 負債合計 (= 純資産 + 当期純利益を集約)
    opening_capital = bs.total_assets - bs.total_liabilities
    return YearEndPreview(
        fiscal_year=fiscal_year,
        next_fiscal_year=fiscal_year + 1,
        balance_forward=items,
        net_income=bs.net_income,
        opening_capital_next=opening_capital,
    )


@router.get("/year-end/carry-forward/preview", response_model=YearEndPreview)
def carry_forward_preview(fiscal_year: int) -> YearEndPreview:
    """年度繰越のドライラン (繰越残高と元入金振替) を返す。

    Args:
        fiscal_year: 繰越元の会計年度。

    Returns:
        翌期へ繰り越す残高と翌期首の元入金。
    """
    return _build_preview(fiscal_year)


@router.post("/year-end/carry-forward", response_model=CarryForwardResult, status_code=201)
def carry_forward(fiscal_year: int) -> CarryForwardResult:
    """年度繰越を実行し、翌年1月1日付の期首振替仕訳を計上する。

    資産を借方・負債を貸方・元入金 (資産−負債) を貸方に置く期首仕訳を作る。これに
    より収益・費用・事業主貸借は元入金へ集約され、翌期の帳簿は繰越残高から始まる。

    Args:
        fiscal_year: 繰越元の会計年度。

    Returns:
        生成した期首振替仕訳と翌期首の元入金。

    Raises:
        HTTPException: 既に繰越済み (409)、または繰越する残高がない (400) の場合。
    """
    if fiscal_year in store.carried_years:
        raise HTTPException(status_code=409, detail=f"{fiscal_year}年度は既に繰越済みです")
    preview = _build_preview(fiscal_year)

    lines: list[JournalLine] = []
    for item in preview.balance_forward:
        if item.closing_balance == 0 or item.account_type == AccountType.EQUITY:
            continue  # 純資産は元入金へ集約するため個別には繰り越さない
        side = Side.DEBIT if item.account_type == AccountType.ASSET else Side.CREDIT
        lines.append(
            JournalLine(side=side, account_code=item.account_code, amount=item.closing_balance)
        )

    capital = preview.opening_capital_next
    if capital > 0:
        lines.append(
            JournalLine(side=Side.CREDIT, account_code=CAPITAL_ACCOUNT_CODE, amount=capital)
        )
    elif capital < 0:
        lines.append(
            JournalLine(side=Side.DEBIT, account_code=CAPITAL_ACCOUNT_CODE, amount=-capital)
        )

    if not lines:
        raise HTTPException(status_code=400, detail="繰越する残高がありません")

    entry = persist_entry(
        date_type(fiscal_year + 1, 1, 1),
        f"前期繰越 ({fiscal_year}年度から)",
        lines,
        source="carry-forward",
    )
    store.carried_years.add(fiscal_year)
    return CarryForwardResult(
        fiscal_year=fiscal_year,
        next_fiscal_year=fiscal_year + 1,
        opening_entry=entry,
        opening_capital_next=capital,
    )
