"""売上・売掛管理の API (M3 receivables)。

役務提供売上を発生主義で計上し (借方:売掛金 / 貸方:売上高)、入金で消し込む
(借方:預金 / 貸方:売掛金)。売掛金は専用テーブルを持たず、勘定科目135の仕訳と
補助科目 (取引先) で取引先別残高を導出する。

由来: 要件定義 F-301/302 / receivables 基本設計 §3。
"""

from collections import defaultdict
from datetime import date as date_type

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.journal import persist_entry
from app.domain.journal import EntryStatus, JournalEntry, JournalLine, Side
from app.services.tax_calc import internal_tax
from app.store import store

router = APIRouter()

RECEIVABLE_CODE = "135"  # 売掛金
SALES_CODE = "500"  # 売上高


class SalesRequest(BaseModel):
    """売上計上リクエスト (発生主義、由来: F-301)。"""

    counterparty: str  # 取引先 (売掛金の補助科目)
    amount: int = Field(gt=0)  # 税込金額
    date: date_type
    description: str
    tax_code: str = "T10"  # 課税売上の税区分


class PaymentRequest(BaseModel):
    """入金消込リクエスト (由来: F-302)。"""

    counterparty: str
    amount: int = Field(gt=0)
    date: date_type
    description: str = "売掛金入金"
    deposit_account_code: str = "102"  # 入金口座 (普通預金/現金)


class OutstandingRow(BaseModel):
    """取引先別の未入金 (売掛残) 1行 (由来: F-302)。"""

    counterparty: str
    balance: int


@router.post("/receivables/sales", response_model=JournalEntry, status_code=201)
def create_sales(payload: SalesRequest) -> JournalEntry:
    """役務提供売上を計上する (借方:売掛金 / 貸方:売上高)。

    Args:
        payload: 取引先・税込金額・日付・摘要・税区分。

    Returns:
        計上された売上仕訳。

    Raises:
        HTTPException: 税区分がマスタに無い場合 (422)。
    """
    if payload.tax_code not in store.tax_categories:
        raise HTTPException(status_code=422, detail=f"未知の税区分: {payload.tax_code}")
    tax = internal_tax(payload.amount, payload.tax_code)
    lines = [
        JournalLine(
            side=Side.DEBIT,
            account_code=RECEIVABLE_CODE,
            sub_account=payload.counterparty,
            amount=payload.amount,
        ),
        JournalLine(
            side=Side.CREDIT,
            account_code=SALES_CODE,
            amount=payload.amount,
            tax_code=payload.tax_code,
            tax_amount=tax,
        ),
    ]
    return persist_entry(payload.date, payload.description, lines, source="receivables-sales")


@router.post("/receivables/payment", response_model=JournalEntry, status_code=201)
def create_payment(payload: PaymentRequest) -> JournalEntry:
    """売掛金の入金を消し込む (借方:預金 / 貸方:売掛金)。

    Args:
        payload: 取引先・入金額・日付・入金口座。

    Returns:
        計上された入金仕訳。

    Raises:
        HTTPException: 入金口座がマスタに無い場合 (422)。
    """
    if payload.deposit_account_code not in store.accounts:
        raise HTTPException(status_code=422, detail=f"未知の口座: {payload.deposit_account_code}")
    lines = [
        JournalLine(
            side=Side.DEBIT, account_code=payload.deposit_account_code, amount=payload.amount
        ),
        JournalLine(
            side=Side.CREDIT,
            account_code=RECEIVABLE_CODE,
            sub_account=payload.counterparty,
            amount=payload.amount,
        ),
    ]
    return persist_entry(payload.date, payload.description, lines, source="receivables-payment")


@router.get("/receivables/outstanding", response_model=list[OutstandingRow])
def outstanding() -> list[OutstandingRow]:
    """取引先別の未入金 (売掛残) 一覧を返す。

    売掛金 (135) の補助科目別残高 = Σ借方 − Σ貸方。残高が正のものだけ返す。

    Returns:
        未入金がある取引先の残高一覧 (残高の降順)。
    """
    balances: dict[str, int] = defaultdict(int)
    for entry in store.journal_entries.values():
        if entry.status == EntryStatus.DELETED:
            continue
        for line in entry.lines:
            if line.account_code != RECEIVABLE_CODE:
                continue
            party = line.sub_account or "(取引先未設定)"
            balances[party] += line.amount if line.side == Side.DEBIT else -line.amount

    rows = [
        OutstandingRow(counterparty=party, balance=balance)
        for party, balance in balances.items()
        if balance != 0
    ]
    return sorted(rows, key=lambda r: r.balance, reverse=True)
