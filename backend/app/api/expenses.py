"""経費・支払の API (M4 expenses)。

経費を科目別に計上し (借方:経費科目 / 貸方:現金・預金・未払金)、未払金は勘定科目
305の仕訳で表現する。専用の経費テーブルは設けない。

由来: 要件定義 F-401/403 / expenses 基本設計 §3。
"""

from collections import defaultdict
from datetime import date as date_type

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.journal import persist_entry
from app.domain.accounts import AccountType
from app.domain.journal import EntryStatus, JournalEntry, JournalLine, Side
from app.services.tax_calc import internal_tax
from app.store import store

router = APIRouter()

PAYABLE_CODE = "305"  # 未払金
CREDIT_CHOICES = ("101", "102", "305")  # 現金 / 普通預金 / 未払金


class ExpenseRequest(BaseModel):
    """経費入力リクエスト (由来: F-401/403)。"""

    expense_account_code: str  # 借方: 経費科目 (601〜690)
    amount: int = Field(gt=0)
    credit_account_code: str = "101"  # 貸方: 現金/預金/未払金
    tax_code: str | None = None  # 省略時は経費科目の既定税区分
    description: str
    date: date_type
    counterparty: str | None = None  # 未払金の補助科目 (任意)


class PayablePaymentRequest(BaseModel):
    """未払金の支払消込リクエスト (由来: F-403)。"""

    counterparty: str
    amount: int = Field(gt=0)
    date: date_type
    description: str = "未払金支払"
    deposit_account_code: str = "102"


class PayableRow(BaseModel):
    """取引先別の未払金残高 1行 (由来: F-403)。"""

    counterparty: str
    balance: int


@router.post("/expenses", response_model=JournalEntry, status_code=201)
def create_expense(payload: ExpenseRequest) -> JournalEntry:
    """経費を計上する (借方:経費科目 / 貸方:現金・預金・未払金)。

    Args:
        payload: 経費科目・金額・貸方科目・税区分・摘要・日付。

    Returns:
        計上された経費仕訳。

    Raises:
        HTTPException: 経費科目が費用でない、または貸方科目が不正な場合 (422)。
    """
    expense = store.accounts.get(payload.expense_account_code)
    if expense is None or expense.type != AccountType.EXPENSE:
        raise HTTPException(status_code=422, detail="借方は費用科目を指定してください")
    if payload.credit_account_code not in CREDIT_CHOICES:
        raise HTTPException(status_code=422, detail="貸方は現金/普通預金/未払金のいずれかです")

    tax_code = payload.tax_code or expense.default_tax_code
    if tax_code is not None and tax_code not in store.tax_categories:
        raise HTTPException(status_code=422, detail=f"未知の税区分: {tax_code}")
    tax = internal_tax(payload.amount, tax_code)

    credit_sub = payload.counterparty if payload.credit_account_code == PAYABLE_CODE else None
    lines = [
        JournalLine(
            side=Side.DEBIT,
            account_code=payload.expense_account_code,
            amount=payload.amount,
            tax_code=tax_code,
            tax_amount=tax,
        ),
        JournalLine(
            side=Side.CREDIT,
            account_code=payload.credit_account_code,
            sub_account=credit_sub,
            amount=payload.amount,
        ),
    ]
    return persist_entry(payload.date, payload.description, lines, source="expenses")


@router.post("/expenses/payment", response_model=JournalEntry, status_code=201)
def pay_payable(payload: PayablePaymentRequest) -> JournalEntry:
    """未払金を支払って消し込む (借方:未払金 / 貸方:預金)。

    Args:
        payload: 取引先・支払額・日付・支払口座。

    Returns:
        計上された支払仕訳。

    Raises:
        HTTPException: 支払口座がマスタに無い場合 (422)。
    """
    if payload.deposit_account_code not in store.accounts:
        raise HTTPException(status_code=422, detail=f"未知の口座: {payload.deposit_account_code}")
    lines = [
        JournalLine(
            side=Side.DEBIT,
            account_code=PAYABLE_CODE,
            sub_account=payload.counterparty,
            amount=payload.amount,
        ),
        JournalLine(
            side=Side.CREDIT, account_code=payload.deposit_account_code, amount=payload.amount
        ),
    ]
    return persist_entry(payload.date, payload.description, lines, source="expenses-payment")


@router.get("/expenses/payables", response_model=list[PayableRow])
def payables() -> list[PayableRow]:
    """取引先別の未払金残高一覧を返す。

    未払金 (305) の補助科目別残高 = Σ貸方 − Σ借方 (負債は貸方が正)。残高が正の
    ものだけ返す。

    Returns:
        未払が残る取引先の残高一覧 (残高の降順)。
    """
    balances: dict[str, int] = defaultdict(int)
    for entry in store.journal_entries.values():
        if entry.status == EntryStatus.DELETED:
            continue
        for line in entry.lines:
            if line.account_code != PAYABLE_CODE:
                continue
            party = line.sub_account or "(取引先未設定)"
            balances[party] += line.amount if line.side == Side.CREDIT else -line.amount

    rows = [
        PayableRow(counterparty=party, balance=balance)
        for party, balance in balances.items()
        if balance != 0
    ]
    return sorted(rows, key=lambda r: r.balance, reverse=True)
