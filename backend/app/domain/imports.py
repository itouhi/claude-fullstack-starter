"""CSV 明細取込のドメインモデル (M5 cash-bank)。

取り込んだ明細は一時的に保持され、確定操作で `JournalEntry` に変換される。

由来: 要件定義 F-503/504 / cash-bank 基本設計 §3.2。
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel


class ImportStatus(StrEnum):
    """取込明細の状態。"""

    PENDING = "pending"  # 未処理 (候補)
    CONFIRMED = "confirmed"  # 確定 (仕訳化済)
    SKIPPED = "skipped"  # スキップ


class BatchStatus(StrEnum):
    """取込バッチの状態。"""

    PENDING = "pending"  # 未確定あり
    COMPLETED = "completed"  # 全明細を処理済


class ImportedTransaction(BaseModel):
    """取込明細 (CSV の1行に対応)。金額は円単位の整数。"""

    id: int
    date: date
    description: str
    payment: int  # 出金額 (0 なら入金行)
    receipt: int  # 入金額 (0 なら出金行)
    balance_ref: int | None = None  # CSV 記載の残高 (参照用)
    suggested_account_code: str | None = None  # 摘要から推測した相手科目
    status: ImportStatus = ImportStatus.PENDING
    journal_entry_id: int | None = None  # 確定後に紐づく仕訳 ID


class ImportBatch(BaseModel):
    """CSV 取込バッチ。明細の一覧を保持する。"""

    id: int
    imported_at: datetime
    account_code: str  # 対象口座の科目コード
    filename: str
    adapter_name: str  # 使用したアダプタ (金融機関識別子)
    status: BatchStatus = BatchStatus.PENDING
    transactions: list[ImportedTransaction]
