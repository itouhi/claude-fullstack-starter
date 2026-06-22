"""帳簿・レポートの API (M7 reports — 仕訳ストアの読み取りビュー)。

由来: 要件定義 F-703 (試算表) / F-701 (仕訳帳) / 全体基本設計 §4.1, §5。
"""

from collections import defaultdict
from datetime import date as date_type

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.domain.accounts import DEBIT_POSITIVE_TYPES, AccountType
from app.domain.journal import EntryStatus, JournalEntry, Side
from app.store import store

router = APIRouter()


class TrialBalanceRow(BaseModel):
    """合計残高試算表の1行 (由来: F-703)。"""

    account_code: str
    account_name: str
    type: AccountType
    debit_total: int
    credit_total: int
    balance: int  # 勘定区分に応じた正残高 (資産・費用は借方、他は貸方が正)


class TrialBalance(BaseModel):
    """合計残高試算表 (由来: F-703)。借方合計と貸方合計は必ず一致する。"""

    fiscal_year: int | None
    rows: list[TrialBalanceRow]
    debit_total: int
    credit_total: int


def _account_order(code: str) -> int:
    """試算表の行ソート用に勘定科目の表示順を返す (未知科目は末尾)。"""
    account = store.accounts.get(code)
    return account.order if account else 9999


def _aggregate(fiscal_year: int | None) -> tuple[dict[str, int], dict[str, int]]:
    """有効な仕訳明細を勘定科目別に借方・貸方へ積み上げて返す。

    PL/BS/試算表などの読み取りビューが共有する集計の起点 (全体基本設計 §4.1)。

    Args:
        fiscal_year: 指定するとその会計年度の仕訳のみを集計する。

    Returns:
        (借方合計の科目別辞書, 貸方合計の科目別辞書)。
    """
    debit: dict[str, int] = defaultdict(int)
    credit: dict[str, int] = defaultdict(int)
    for entry in store.journal_entries.values():
        if entry.status == EntryStatus.DELETED:
            continue
        if fiscal_year is not None and entry.fiscal_year != fiscal_year:
            continue
        for line in entry.lines:
            if line.side == Side.DEBIT:
                debit[line.account_code] += line.amount
            else:
                credit[line.account_code] += line.amount
    return debit, credit


def _balance_of(code: str, debit: dict[str, int], credit: dict[str, int]) -> int:
    """勘定区分に応じた正残高を返す (資産・費用は借方、他は貸方が正)。"""
    account = store.accounts.get(code)
    account_type = account.type if account else AccountType.ASSET
    d, c = debit[code], credit[code]
    return d - c if account_type in DEBIT_POSITIVE_TYPES else c - d


@router.get("/reports/trial-balance", response_model=TrialBalance)
def trial_balance(fiscal_year: int | None = None) -> TrialBalance:
    """合計残高試算表を集計して返す。

    有効な全仕訳の明細を勘定科目別に借方・貸方へ積み上げ、勘定区分に応じた
    正残高を算出する。

    Args:
        fiscal_year: 指定するとその会計年度の仕訳のみを集計する。

    Returns:
        勘定科目別の借方合計・貸方合計・残高と、全体の借貸合計。
    """
    debit, credit = _aggregate(fiscal_year)

    rows: list[TrialBalanceRow] = []
    for code in sorted(set(debit) | set(credit), key=_account_order):
        account = store.accounts.get(code)
        d, c = debit[code], credit[code]
        account_type = account.type if account else AccountType.ASSET
        balance = d - c if account_type in DEBIT_POSITIVE_TYPES else c - d
        rows.append(
            TrialBalanceRow(
                account_code=code,
                account_name=account.name if account else code,
                type=account_type,
                debit_total=d,
                credit_total=c,
                balance=balance,
            )
        )

    return TrialBalance(
        fiscal_year=fiscal_year,
        rows=rows,
        debit_total=sum(debit.values()),
        credit_total=sum(credit.values()),
    )


class ReportRow(BaseModel):
    """損益計算書・貸借対照表の1行 (勘定科目と正残高)。"""

    account_code: str
    account_name: str
    amount: int


class ProfitAndLoss(BaseModel):
    """損益計算書 (PL、由来: F-704)。当期純利益 = 収益合計 − 費用合計。"""

    fiscal_year: int | None
    revenues: list[ReportRow]
    expenses: list[ReportRow]
    total_revenue: int
    total_expense: int
    net_income: int


class BalanceSheet(BaseModel):
    """貸借対照表 (BS、由来: F-705)。資産 = 負債 + 純資産 (当期純利益を含む)。"""

    fiscal_year: int | None
    assets: list[ReportRow]
    liabilities: list[ReportRow]
    equity: list[ReportRow]
    total_assets: int
    total_liabilities: int
    total_equity: int  # 純資産 (当期純利益を含む)
    net_income: int


def _rows_for_types(
    types: set[AccountType], debit: dict[str, int], credit: dict[str, int]
) -> list[ReportRow]:
    """指定区分の勘定科目について、残高が非ゼロの行を表示順で返す。"""
    codes = {
        code
        for code in set(debit) | set(credit)
        if (store.accounts.get(code) and store.accounts[code].type in types)
    }
    rows: list[ReportRow] = []
    for code in sorted(codes, key=_account_order):
        amount = _balance_of(code, debit, credit)
        if amount == 0:
            continue
        rows.append(
            ReportRow(account_code=code, account_name=store.accounts[code].name, amount=amount)
        )
    return rows


class GeneralLedgerRow(BaseModel):
    """総勘定元帳の1行 (由来: reports BD-103)。"""

    date: date_type
    entry_id: int
    description: str
    counter_account: str  # 相手科目名 (複合仕訳は「諸口」)
    debit_amount: int
    credit_amount: int
    running_balance: int  # 期首繰越 + 当行までの正残高累計


class GeneralLedger(BaseModel):
    """総勘定元帳 (科目別の元帳、由来: F-702)。"""

    account_code: str
    account_name: str
    fiscal_year: int | None
    opening_balance: int
    rows: list[GeneralLedgerRow]
    closing_balance: int


def _ledger_counter_name(entry: JournalEntry, account_code: str) -> str:
    """対象科目から見た相手科目名を返す (相手が複数なら「諸口」)。"""
    others = [line for line in entry.lines if line.account_code != account_code]
    if len(others) == 1:
        account = store.accounts.get(others[0].account_code)
        return account.name if account else others[0].account_code
    return "諸口"


@router.get("/reports/general-ledger", response_model=GeneralLedger)
def general_ledger(account_code: str, fiscal_year: int | None = None) -> GeneralLedger:
    """指定科目の総勘定元帳を時系列で返す。

    対象科目を含む有効な仕訳を日付順に並べ、勘定区分の正残高で繰越残高を
    積み上げる (資産・費用は借方、他は貸方が正)。

    Args:
        account_code: 対象の勘定科目コード。
        fiscal_year: 指定するとその会計年度の仕訳のみを対象にする。

    Returns:
        科目名・期首繰越・元帳の行・期末残高。

    Raises:
        HTTPException: 勘定科目が存在しない場合 (404)。
    """
    account = store.accounts.get(account_code)
    if account is None:
        raise HTTPException(status_code=404, detail="勘定科目が見つかりません")
    debit_positive = account.type in DEBIT_POSITIVE_TYPES

    entries = [
        e
        for e in store.journal_entries.values()
        if e.status != EntryStatus.DELETED
        and (fiscal_year is None or e.fiscal_year == fiscal_year)
        and any(line.account_code == account_code for line in e.lines)
    ]
    entries.sort(key=lambda e: (e.date, e.id))

    opening_balance = 0  # 期首残高マスタ未実装の間は 0 (BD-103)
    balance = opening_balance
    rows: list[GeneralLedgerRow] = []
    for entry in entries:
        debit = sum(
            line.amount
            for line in entry.lines
            if line.account_code == account_code and line.side == Side.DEBIT
        )
        credit = sum(
            line.amount
            for line in entry.lines
            if line.account_code == account_code and line.side == Side.CREDIT
        )
        balance += (debit - credit) if debit_positive else (credit - debit)
        rows.append(
            GeneralLedgerRow(
                date=entry.date,
                entry_id=entry.id,
                description=entry.description,
                counter_account=_ledger_counter_name(entry, account_code),
                debit_amount=debit,
                credit_amount=credit,
                running_balance=balance,
            )
        )

    return GeneralLedger(
        account_code=account_code,
        account_name=account.name,
        fiscal_year=fiscal_year,
        opening_balance=opening_balance,
        rows=rows,
        closing_balance=balance,
    )


@router.get("/reports/pl", response_model=ProfitAndLoss)
def profit_and_loss(fiscal_year: int | None = None) -> ProfitAndLoss:
    """損益計算書を集計して返す。

    収益・費用区分の科目残高を積み上げ、当期純利益を算出する。

    Args:
        fiscal_year: 指定するとその会計年度の仕訳のみを集計する。

    Returns:
        収益行・費用行と、収益合計・費用合計・当期純利益。
    """
    debit, credit = _aggregate(fiscal_year)
    revenues = _rows_for_types({AccountType.REVENUE}, debit, credit)
    expenses = _rows_for_types({AccountType.EXPENSE}, debit, credit)
    total_revenue = sum(r.amount for r in revenues)
    total_expense = sum(r.amount for r in expenses)
    return ProfitAndLoss(
        fiscal_year=fiscal_year,
        revenues=revenues,
        expenses=expenses,
        total_revenue=total_revenue,
        total_expense=total_expense,
        net_income=total_revenue - total_expense,
    )


@router.get("/reports/bs", response_model=BalanceSheet)
def balance_sheet(fiscal_year: int | None = None) -> BalanceSheet:
    """貸借対照表を集計して返す。

    資産・負債・純資産区分の科目残高を積み上げる。当期純利益 (収益−費用) を
    純資産の部に含め、資産合計 = 負債合計 + 純資産合計 が成り立つ。

    Args:
        fiscal_year: 指定するとその会計年度の仕訳のみを集計する。

    Returns:
        資産行・負債行・純資産行と各合計、当期純利益。
    """
    debit, credit = _aggregate(fiscal_year)
    assets = _rows_for_types({AccountType.ASSET}, debit, credit)
    liabilities = _rows_for_types({AccountType.LIABILITY}, debit, credit)
    equity = _rows_for_types({AccountType.EQUITY}, debit, credit)
    revenues = _rows_for_types({AccountType.REVENUE}, debit, credit)
    expenses = _rows_for_types({AccountType.EXPENSE}, debit, credit)
    net_income = sum(r.amount for r in revenues) - sum(r.amount for r in expenses)
    total_equity = sum(e.amount for e in equity) + net_income
    return BalanceSheet(
        fiscal_year=fiscal_year,
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        total_assets=sum(a.amount for a in assets),
        total_liabilities=sum(line.amount for line in liabilities),
        total_equity=total_equity,
        net_income=net_income,
    )
