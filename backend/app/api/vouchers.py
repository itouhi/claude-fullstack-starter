"""証憑保存・検索の API (X3 — 電子帳簿保存法対応)。

証憑を登録し、電帳法が求める3キー (取引日・金額・取引先) で検索できる。

由来: 要件定義 F-402 / N-5 / closing-tax・expenses 基本設計 (証憑保存)。
"""

from datetime import date as date_type

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.domain.voucher import Voucher
from app.store import now, store

router = APIRouter()


class VoucherCreate(BaseModel):
    """証憑の登録リクエスト (由来: F-402)。"""

    transaction_date: date_type
    amount: int = Field(ge=0)
    counterparty: str
    file_name: str
    content_base64: str | None = None
    journal_entry_id: int | None = None


@router.post("/vouchers", response_model=Voucher, status_code=201)
def create_voucher(payload: VoucherCreate) -> Voucher:
    """証憑を登録する。紐づく仕訳がある場合は存在を検証する。

    Args:
        payload: 取引日・金額・取引先・ファイル名など。

    Returns:
        採番・登録された証憑。

    Raises:
        HTTPException: 紐づけ先の仕訳が存在しない場合 (422)。
    """
    if (
        payload.journal_entry_id is not None
        and payload.journal_entry_id not in store.journal_entries
    ):
        raise HTTPException(status_code=422, detail="紐づけ先の仕訳が存在しません")
    voucher = Voucher(
        id=store.next_voucher_id(),
        transaction_date=payload.transaction_date,
        amount=payload.amount,
        counterparty=payload.counterparty,
        file_name=payload.file_name,
        content_base64=payload.content_base64,
        journal_entry_id=payload.journal_entry_id,
        created_at=now(),
    )
    store.vouchers[voucher.id] = voucher
    return voucher


@router.get("/vouchers", response_model=list[Voucher])
def search_vouchers(
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    amount: int | None = None,
    counterparty: str | None = None,
) -> list[Voucher]:
    """証憑を電帳法の3キー (取引日・金額・取引先) で検索する。

    Args:
        date_from: 取引日の下限 (含む)。
        date_to: 取引日の上限 (含む)。
        amount: 金額の完全一致。
        counterparty: 取引先の部分一致。

    Returns:
        条件に合致する証憑を取引日昇順で返す。
    """
    results = []
    for voucher in store.vouchers.values():
        if date_from is not None and voucher.transaction_date < date_from:
            continue
        if date_to is not None and voucher.transaction_date > date_to:
            continue
        if amount is not None and voucher.amount != amount:
            continue
        if counterparty is not None and counterparty not in voucher.counterparty:
            continue
        results.append(voucher)
    return sorted(results, key=lambda v: (v.transaction_date, v.id))
