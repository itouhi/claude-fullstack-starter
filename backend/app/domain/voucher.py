"""証憑のドメインモデル (X3 — 電子帳簿保存法対応)。

領収書・請求書の画像/PDF を取引に紐づけて保存する。電帳法の検索要件
(取引日・金額・取引先) を満たすためのメタデータを保持する。

由来: 要件定義 F-402 / N-5 / 全体基本設計 §4, §7 (X3)。
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class Voucher(BaseModel):
    """証憑。電帳法の検索キー (取引日・金額・取引先) を必須メタデータとする。

    ファイル実体は `content_base64` に保持する (将来は外部ストレージへ)。
    """

    id: int
    transaction_date: date  # 取引日 (検索キー)
    amount: int = Field(ge=0)  # 金額 (検索キー)
    counterparty: str  # 取引先 (検索キー)
    file_name: str
    content_base64: str | None = None  # ファイル実体 (任意)
    journal_entry_id: int | None = None  # 紐づく仕訳
    created_at: datetime
