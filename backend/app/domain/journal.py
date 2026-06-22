"""仕訳のドメインモデル (共通基盤 M2 — 仕訳エンジン)。

複式簿記の中核。すべての取引はここに正規化され、帳簿・レポート・申告集計は
この仕訳ストアからの読み取りビューとして実装される。

由来: 要件定義 F-101 / B-1 / 全体基本設計 §1.3, §4。
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class Side(StrEnum):
    """仕訳明細の貸借区分。"""

    DEBIT = "debit"  # 借方
    CREDIT = "credit"  # 貸方


class EntryStatus(StrEnum):
    """仕訳の状態 (訂正履歴の論理管理、由来: F-103)。"""

    ACTIVE = "active"  # 有効
    CORRECTED = "corrected"  # 訂正により旧版となった
    DELETED = "deleted"  # 論理削除


class JournalLine(BaseModel):
    """仕訳明細。1仕訳に複数。金額は円単位の整数 (JPY に補助単位なし)。

    由来: データ要件「仕訳明細」/ F-204 (税区分・税額)。
    """

    side: Side
    account_code: str
    sub_account: str | None = None
    amount: int = Field(gt=0, description="金額 (円、正の整数)")
    tax_code: str | None = None
    tax_amount: int = 0


class JournalEntry(BaseModel):
    """仕訳 (複式簿記の基本単位)。

    不変条件: 借方金額合計 == 貸方金額合計 (借貸平均の原理)。生成時に検証する。

    由来: F-101 / B-1 / 全体基本設計 §4。
    """

    id: int
    date: date
    description: str
    fiscal_year: int
    lines: list[JournalLine]
    source: str = "manual"  # 由来 (manual / cash-book / depreciation / ...)
    status: EntryStatus = EntryStatus.ACTIVE
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _check_balanced(self) -> JournalEntry:
        """借方=貸方 かつ 明細が借方・貸方を両方含むことを検証する。"""
        if not self.lines:
            raise ValueError("仕訳明細が空です")
        debit = sum(line.amount for line in self.lines if line.side == Side.DEBIT)
        credit = sum(line.amount for line in self.lines if line.side == Side.CREDIT)
        if debit == 0 or credit == 0:
            raise ValueError("借方と貸方の両方に明細が必要です")
        if debit != credit:
            raise ValueError(f"借方合計({debit})と貸方合計({credit})が一致しません")
        return self
