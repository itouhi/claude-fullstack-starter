"""CSV 明細取込・消込の API (M5 cash-bank)。

銀行・カードの CSV を取り込んで仕訳候補化し (F-503)、候補を確定すると複式仕訳に
変換して登録する (F-504)。相手科目は摘要から自動推測した候補を提示する (F-105)。

由来: 要件定義 F-503/504 / cash-bank 基本設計 §4, §5.3。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.journal import persist_entry
from app.domain.accounts import AccountType
from app.domain.imports import (
    BatchStatus,
    ImportBatch,
    ImportedTransaction,
    ImportStatus,
)
from app.domain.journal import JournalEntry, JournalLine, Side
from app.services.csv_import import parse_csv
from app.store import now, store

router = APIRouter()


class ImportRequest(BaseModel):
    """CSV 取込リクエスト (由来: BD-104)。

    ファイルアップロードの代わりに CSV 本文を文字列で受け取る (依存追加を避ける)。
    """

    account_code: str  # 対象口座 (現金101 / 預金102 など)
    csv_text: str
    adapter: str = "sbi"
    filename: str = "import.csv"


class ConfirmRequest(BaseModel):
    """取込明細の確定リクエスト。相手科目を上書き指定できる。"""

    counter_code: str | None = None  # 省略時は推測科目を使用


def _get_batch(batch_id: int) -> ImportBatch:
    """取込バッチを取得する (なければ 404)。"""
    batch = store.import_batches.get(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="取込バッチが見つかりません")
    return batch


def _refresh_batch_status(batch: ImportBatch) -> None:
    """全明細が処理済みならバッチを完了状態にする。"""
    if all(tx.status != ImportStatus.PENDING for tx in batch.transactions):
        batch.status = BatchStatus.COMPLETED


@router.post("/imports/csv", response_model=ImportBatch, status_code=201)
def import_csv(payload: ImportRequest) -> ImportBatch:
    """CSV を取り込み、明細を仕訳候補として返す。

    Args:
        payload: 対象口座・CSV本文・アダプタ・ファイル名。

    Returns:
        採番された取込バッチ (相手科目を推測した明細候補を含む)。

    Raises:
        HTTPException: 口座が存在しない、またはアダプタが未対応の場合 (422)。
    """
    if payload.account_code not in store.accounts:
        raise HTTPException(status_code=422, detail=f"未知の口座: {payload.account_code}")
    try:
        parsed = parse_csv(payload.csv_text, payload.adapter)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    transactions = [
        ImportedTransaction(
            id=store.next_tx_id(),
            date=row.date,
            description=row.description,
            payment=row.payment,
            receipt=row.receipt,
            balance_ref=row.balance_ref,
            suggested_account_code=row.suggested_account_code,
        )
        for row in parsed
    ]
    batch = ImportBatch(
        id=store.next_batch_id(),
        imported_at=now(),
        account_code=payload.account_code,
        filename=payload.filename,
        adapter_name=payload.adapter,
        transactions=transactions,
    )
    store.import_batches[batch.id] = batch
    return batch


@router.get("/imports/{batch_id}", response_model=ImportBatch)
def get_batch(batch_id: int) -> ImportBatch:
    """取込バッチの明細とステータスを返す。

    Args:
        batch_id: 取込バッチ ID。

    Returns:
        取込バッチ。
    """
    return _get_batch(batch_id)


def _find_tx(batch: ImportBatch, tx_id: int) -> ImportedTransaction:
    """バッチ内の取込明細を取得する (なければ 404)。"""
    for tx in batch.transactions:
        if tx.id == tx_id:
            return tx
    raise HTTPException(status_code=404, detail="取込明細が見つかりません")


@router.post(
    "/imports/{batch_id}/transactions/{tx_id}/confirm",
    response_model=JournalEntry,
    status_code=201,
)
def confirm_transaction(batch_id: int, tx_id: int, payload: ConfirmRequest) -> JournalEntry:
    """取込明細を確定し、複式仕訳に変換して登録する。

    入金行は「借方:口座 / 貸方:相手科目」、出金行は「借方:相手科目 / 貸方:口座」。
    相手科目は指定値、なければ推測科目を用いる。

    Args:
        batch_id: 取込バッチ ID。
        tx_id: 取込明細 ID。
        payload: 相手科目の上書き指定 (任意)。

    Returns:
        生成・登録された仕訳。

    Raises:
        HTTPException: 既に処理済み・相手科目が未確定・科目が不正な場合 (409/422)。
    """
    batch = _get_batch(batch_id)
    tx = _find_tx(batch, tx_id)
    if tx.status != ImportStatus.PENDING:
        raise HTTPException(status_code=409, detail="この明細は既に処理済みです")

    counter_code = payload.counter_code or tx.suggested_account_code
    if counter_code is None:
        raise HTTPException(status_code=422, detail="相手科目を指定してください")
    counter = store.accounts.get(counter_code)
    if counter is None:
        raise HTTPException(status_code=422, detail=f"未知の相手科目: {counter_code}")

    amount = tx.receipt if tx.receipt > 0 else tx.payment
    is_receipt = tx.receipt > 0
    tax_code = counter.default_tax_code if counter.type != AccountType.ASSET else None
    account_line = JournalLine(side=Side.DEBIT, account_code=batch.account_code, amount=amount)
    counter_line = JournalLine(
        side=Side.CREDIT, account_code=counter_code, amount=amount, tax_code=tax_code
    )
    if is_receipt:
        lines = [account_line, counter_line]
    else:
        account_line.side = Side.CREDIT
        counter_line.side = Side.DEBIT
        lines = [counter_line, account_line]

    entry = persist_entry(tx.date, tx.description, lines, source="csv-import")
    tx.status = ImportStatus.CONFIRMED
    tx.journal_entry_id = entry.id
    _refresh_batch_status(batch)
    return entry


@router.post("/imports/{batch_id}/transactions/{tx_id}/skip", response_model=ImportedTransaction)
def skip_transaction(batch_id: int, tx_id: int) -> ImportedTransaction:
    """取込明細をスキップ (仕訳化しない) する。

    Args:
        batch_id: 取込バッチ ID。
        tx_id: 取込明細 ID。

    Returns:
        スキップ後の取込明細。

    Raises:
        HTTPException: 既に処理済みの場合 (409)。
    """
    batch = _get_batch(batch_id)
    tx = _find_tx(batch, tx_id)
    if tx.status != ImportStatus.PENDING:
        raise HTTPException(status_code=409, detail="この明細は既に処理済みです")
    tx.status = ImportStatus.SKIPPED
    _refresh_batch_status(batch)
    return tx
