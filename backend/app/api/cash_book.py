"""出納帳の API (M5 cash-bank)。

現金・預金の出納帳を仕訳ストアの読み取りビューとして提供し、簿記非専門でも
記帳できる簡易入力 (入金/出金) を2明細の複式仕訳に変換して登録する。

由来: 要件定義 F-501/F-502 (出納帳) / F-102 (簡易入力) / N-9 /
      cash-bank 基本設計 BD-101, BD-102。
"""

from datetime import date as date_type
from enum import StrEnum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.journal import persist_entry
from app.domain.accounts import AccountType
from app.domain.journal import EntryStatus, JournalEntry, JournalLine, Side
from app.store import store

router = APIRouter()


class CashBookRow(BaseModel):
    """出納帳の1行 (由来: cash-bank BD-101)。"""

    date: date_type
    description: str
    counter_account: str  # 相手科目名 (複合仕訳は「諸口」)
    receipt: int  # 入金額 (対象口座が借方)
    payment: int  # 出金額 (対象口座が貸方)
    balance: int  # 当行までの残高
    journal_entry_id: int


class CashBook(BaseModel):
    """出納帳 (口座別の入出金と残高、由来: F-501/F-502)。"""

    account_code: str
    account_name: str
    opening_balance: int  # 期首残高 (M1 OpeningBalance 未実装の間は 0)
    rows: list[CashBookRow]
    closing_balance: int


class CashDirection(StrEnum):
    """簡易入力の入出金方向。"""

    RECEIPT = "receipt"  # 入金
    PAYMENT = "payment"  # 出金


class CashEntryRequest(BaseModel):
    """出納帳の簡易入力リクエスト (由来: F-102 / BD-102)。

    借方/貸方を意識せず、入金/出金と相手科目だけで記帳できる。
    """

    account_code: str  # 現金(101) または預金科目コード
    direction: CashDirection
    counter_code: str  # 相手科目コード
    amount: int = Field(gt=0)
    description: str
    date: date_type
    tax_code: str | None = None  # 省略時は相手科目の既定税区分を使用


def _counter_account_name(entry: JournalEntry, account_code: str) -> str:
    """対象口座から見た相手科目名を返す (相手が複数なら「諸口」)。"""
    others = [line for line in entry.lines if line.account_code != account_code]
    if len(others) == 1:
        account = store.accounts.get(others[0].account_code)
        return account.name if account else others[0].account_code
    return "諸口"


@router.get("/cash-book/{account_code}", response_model=CashBook)
def cash_book(account_code: str, fiscal_year: int | None = None) -> CashBook:
    """指定口座の出納帳を時系列で返す。

    対象口座 (現金・預金) を含む有効な仕訳を日付順に並べ、借方を入金・貸方を
    出金として残高を積み上げる。

    Args:
        account_code: 口座の勘定科目コード (例: 101 現金 / 102 普通預金)。
        fiscal_year: 指定するとその会計年度の仕訳のみを対象にする。

    Returns:
        口座名・期首残高・出納帳の行・期末残高。

    Raises:
        HTTPException: 勘定科目が存在しない場合 (404)。
    """
    account = store.accounts.get(account_code)
    if account is None:
        raise HTTPException(status_code=404, detail="勘定科目が見つかりません")

    entries = [
        e
        for e in store.journal_entries.values()
        if e.status != EntryStatus.DELETED
        and (fiscal_year is None or e.fiscal_year == fiscal_year)
        and any(line.account_code == account_code for line in e.lines)
    ]
    entries.sort(key=lambda e: (e.date, e.id))

    opening_balance = 0  # M1 期首残高は未実装のため 0 (BD-101)
    balance = opening_balance
    rows: list[CashBookRow] = []
    for entry in entries:
        receipt = sum(
            line.amount
            for line in entry.lines
            if line.account_code == account_code and line.side == Side.DEBIT
        )
        payment = sum(
            line.amount
            for line in entry.lines
            if line.account_code == account_code and line.side == Side.CREDIT
        )
        balance += receipt - payment
        rows.append(
            CashBookRow(
                date=entry.date,
                description=entry.description,
                counter_account=_counter_account_name(entry, account_code),
                receipt=receipt,
                payment=payment,
                balance=balance,
                journal_entry_id=entry.id,
            )
        )

    return CashBook(
        account_code=account_code,
        account_name=account.name,
        opening_balance=opening_balance,
        rows=rows,
        closing_balance=balance,
    )


@router.post("/cash-book/entries", response_model=JournalEntry, status_code=201)
def create_cash_entry(payload: CashEntryRequest) -> JournalEntry:
    """簡易入力 (入金/出金) を2明細の複式仕訳に変換して登録する。

    入金は「借方:口座 / 貸方:相手科目」、出金は「借方:相手科目 / 貸方:口座」。
    相手科目の明細には税区分を付す (省略時は相手科目の既定税区分)。

    Args:
        payload: 口座・入出金方向・相手科目・金額・摘要・日付。

    Returns:
        生成・登録された仕訳。

    Raises:
        HTTPException: 口座が現金・預金 (資産) でない、または相手科目が無い場合 (422)。
    """
    account = store.accounts.get(payload.account_code)
    if account is None or account.type != AccountType.ASSET:
        raise HTTPException(
            status_code=422, detail="口座は資産科目 (現金・預金) を指定してください"
        )
    counter = store.accounts.get(payload.counter_code)
    if counter is None:
        raise HTTPException(status_code=422, detail=f"未知の相手科目: {payload.counter_code}")

    tax_code = payload.tax_code or counter.default_tax_code
    account_line = JournalLine(
        side=Side.DEBIT, account_code=payload.account_code, amount=payload.amount
    )
    counter_line = JournalLine(
        side=Side.CREDIT,
        account_code=payload.counter_code,
        amount=payload.amount,
        tax_code=tax_code,
    )
    if payload.direction == CashDirection.RECEIPT:
        lines = [account_line, counter_line]
    else:
        # 出金: 口座を貸方、相手科目を借方にする
        account_line.side = Side.CREDIT
        counter_line.side = Side.DEBIT
        lines = [counter_line, account_line]

    return persist_entry(payload.date, payload.description, lines, source="cash-book")
