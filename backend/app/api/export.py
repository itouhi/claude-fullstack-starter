"""帳簿・決算書の CSV エクスポート API (M9 data-io)。

M7 の集計結果を CSV に変換し、税理士共有用に出力する。集計は再実装せず M7 の
関数をそのまま利用する。PDF は将来対応 (501)。

由来: 要件定義 F-902 / N-8 / data-io 基本設計 §1.1, §4。
"""

import csv
import io

from fastapi import APIRouter, HTTPException, Response

from app.api.journal import list_journal_entries
from app.api.reports import balance_sheet, profit_and_loss, trial_balance
from app.store import store

router = APIRouter()

SUPPORTED_REPORTS = ("journal", "trial-balance", "pl", "bs")


def _journal_csv(fiscal_year: int | None) -> list[list[object]]:
    """仕訳帳の CSV 行 (ヘッダ + 明細) を生成する。"""
    rows: list[list[object]] = [["日付", "摘要", "借貸", "勘定科目", "金額", "税区分"]]
    for entry in list_journal_entries(fiscal_year):
        for line in entry.lines:
            account = store.accounts.get(line.account_code)
            rows.append(
                [
                    entry.date.isoformat(),
                    entry.description,
                    "借方" if line.side == "debit" else "貸方",
                    account.name if account else line.account_code,
                    line.amount,
                    line.tax_code or "",
                ]
            )
    return rows


def _trial_balance_csv(fiscal_year: int | None) -> list[list[object]]:
    """合計残高試算表の CSV 行を生成する。"""
    tb = trial_balance(fiscal_year)
    rows: list[list[object]] = [["勘定科目", "借方合計", "貸方合計", "残高"]]
    for row in tb.rows:
        rows.append([row.account_name, row.debit_total, row.credit_total, row.balance])
    rows.append(["合計", tb.debit_total, tb.credit_total, ""])
    return rows


def _pl_csv(fiscal_year: int | None) -> list[list[object]]:
    """損益計算書の CSV 行を生成する。"""
    pl = profit_and_loss(fiscal_year)
    rows: list[list[object]] = [["区分", "勘定科目", "金額"]]
    for row in pl.revenues:
        rows.append(["収益", row.account_name, row.amount])
    rows.append(["", "収益合計", pl.total_revenue])
    for row in pl.expenses:
        rows.append(["費用", row.account_name, row.amount])
    rows.append(["", "費用合計", pl.total_expense])
    rows.append(["", "当期純利益", pl.net_income])
    return rows


def _bs_csv(fiscal_year: int | None) -> list[list[object]]:
    """貸借対照表の CSV 行を生成する。"""
    bs = balance_sheet(fiscal_year)
    rows: list[list[object]] = [["区分", "勘定科目", "金額"]]
    for row in bs.assets:
        rows.append(["資産", row.account_name, row.amount])
    rows.append(["", "資産合計", bs.total_assets])
    for row in bs.liabilities:
        rows.append(["負債", row.account_name, row.amount])
    for row in bs.equity:
        rows.append(["純資産", row.account_name, row.amount])
    rows.append(["純資産", "当期純利益", bs.net_income])
    rows.append(["", "負債・純資産合計", bs.total_liabilities + bs.total_equity])
    return rows


_BUILDERS = {
    "journal": _journal_csv,
    "trial-balance": _trial_balance_csv,
    "pl": _pl_csv,
    "bs": _bs_csv,
}


@router.get("/export/{report}")
def export_report(report: str, fiscal_year: int | None = None, format: str = "csv") -> Response:
    """帳簿・決算書を CSV で出力する。

    Args:
        report: 出力対象 (journal / trial-balance / pl / bs)。
        fiscal_year: 会計年度で絞り込む (任意)。
        format: 出力形式。現在は csv のみ (pdf は未実装)。

    Returns:
        UTF-8 (BOM付き) の CSV を持つ Response。

    Raises:
        HTTPException: 未知のレポート (404)・未実装形式 (501)・不正な形式 (422)。
    """
    if report not in SUPPORTED_REPORTS:
        raise HTTPException(status_code=404, detail=f"未知のレポート: {report}")
    if format == "pdf":
        raise HTTPException(status_code=501, detail="PDF 出力は未実装です")
    if format != "csv":
        raise HTTPException(status_code=422, detail=f"未対応の形式: {format}")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerows(_BUILDERS[report](fiscal_year))
    # Excel で文字化けしないよう BOM 付き UTF-8 で返す
    content = "﻿" + buffer.getvalue()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{report}.csv"'},
    )
