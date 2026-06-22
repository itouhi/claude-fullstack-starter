"""銀行・カード CSV 明細のパーサ (M5 — アダプタ方式)。

金融機関ごとに CSV の体裁が異なるため、アダプタで差異を吸収する。初期実装は
住信SBIネット銀行形式 (日付,摘要,出金,入金,残高) を基準とする。

由来: 要件定義 F-503 / cash-bank 基本設計 §5.4。
"""

import csv
import io
from datetime import date

from app.services.account_suggester import suggest_account


class ParsedRow:
    """パース済みの1明細 (API 層で ImportedTransaction に変換する中間表現)。"""

    def __init__(
        self,
        row_date: date,
        description: str,
        payment: int,
        receipt: int,
        balance_ref: int | None,
        suggested_account_code: str | None,
    ) -> None:
        self.date = row_date
        self.description = description
        self.payment = payment
        self.receipt = receipt
        self.balance_ref = balance_ref
        self.suggested_account_code = suggested_account_code


def _parse_amount(value: str) -> int:
    """金額セルを整数に変換する (空白・カンマ・全角空白を許容、空は0)。"""
    cleaned = value.strip().replace(",", "").replace("　", "")
    return int(cleaned) if cleaned else 0


def _parse_date(value: str) -> date:
    """日付セルを date に変換する (`YYYY-MM-DD` / `YYYY/MM/DD`)。"""
    return date.fromisoformat(value.strip().replace("/", "-"))


#: 対応アダプタ (列順: 日付, 摘要, 出金, 入金, 残高)
SUPPORTED_ADAPTERS = {"sbi", "generic"}


def parse_csv(text: str, adapter: str = "sbi") -> list[ParsedRow]:
    """CSV テキストを明細行に変換し、相手科目を推測して付与する。

    ヘッダ行 (先頭セルが日付として解釈できない行) は読み飛ばす。

    Args:
        text: CSV 全文。
        adapter: 金融機関アダプタ識別子 (現在は SBI 互換の列順を共通利用)。

    Returns:
        パース済み明細行の一覧。

    Raises:
        ValueError: 未対応のアダプタが指定された場合。
    """
    if adapter not in SUPPORTED_ADAPTERS:
        raise ValueError(f"未対応のアダプタです: {adapter}")

    rows: list[ParsedRow] = []
    for cells in csv.reader(io.StringIO(text)):
        if len(cells) < 4:
            continue
        try:
            row_date = _parse_date(cells[0])
        except ValueError:
            continue  # ヘッダ行など
        description = cells[1].strip()
        rows.append(
            ParsedRow(
                row_date=row_date,
                description=description,
                payment=_parse_amount(cells[2]),
                receipt=_parse_amount(cells[3]),
                balance_ref=_parse_amount(cells[4]) if len(cells) > 4 else None,
                suggested_account_code=suggest_account(description),
            )
        )
    return rows
