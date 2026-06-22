"""消費税 (簡易課税) 集計の API (M8 closing-tax)。

課税売上を税率別に集計し、みなし仕入率 (サービス業=第五種50%) で控除税額・納付
税額を計算する。納付確定時は仕訳を計上する。

由来: 要件定義 F-804 / 全体基本設計 §4.2 / closing-tax 基本設計 §5。
"""

from datetime import date as date_type

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.journal import persist_entry
from app.domain.journal import EntryStatus, JournalLine, Side
from app.store import store

router = APIRouter()

SALES_ACCOUNT_CODE = "500"  # 売上高
DEEMED_PURCHASE_RATE = 0.5  # みなし仕入率 (第五種=50%)
BUSINESS_TYPE = 5  # 事業区分 (サービス業=第五種)
SALES_TAX_CODES = ("T10", "T08")  # 課税売上の税区分
TAX_PAYABLE_CODE = "330"  # 未払消費税
TAX_EXPENSE_CODE = "601"  # 租税公課


class TaxRateLine(BaseModel):
    """税率別の消費税集計 (由来: closing-tax BD-103)。"""

    rate_percent: int
    tax_code: str
    taxable_sales_base: int  # 課税売上 (税抜)
    tax_amount: int  # 消費税額
    deductible_amount: int  # 控除税額 (× みなし仕入率)
    payable_amount: int  # 納付税額


class ConsumptionTax(BaseModel):
    """消費税 (簡易課税) 集計結果 (由来: F-804)。"""

    fiscal_year: int
    business_type: int
    deemed_purchase_rate: float
    tax_rates: list[TaxRateLine]
    total_tax_amount: int
    total_deductible_amount: int
    total_payable_amount: int


def _calc_consumption_tax(fiscal_year: int) -> ConsumptionTax:
    """課税売上の税区分別に消費税額・控除税額・納付税額を集計する。

    消費税額は売上明細の `tax_amount` を積み上げ (逆算しない)。控除税額は
    みなし仕入率を乗じて切り捨てる (全体基本設計 §4.2)。
    """
    base: dict[str, int] = {code: 0 for code in SALES_TAX_CODES}
    tax: dict[str, int] = {code: 0 for code in SALES_TAX_CODES}
    for entry in store.journal_entries.values():
        if entry.status == EntryStatus.DELETED or entry.fiscal_year != fiscal_year:
            continue
        for line in entry.lines:
            if (
                line.account_code == SALES_ACCOUNT_CODE
                and line.side == Side.CREDIT
                and line.tax_code in SALES_TAX_CODES
            ):
                tax[line.tax_code] += line.tax_amount
                base[line.tax_code] += line.amount - line.tax_amount  # 税抜

    rate_lines: list[TaxRateLine] = []
    for code in SALES_TAX_CODES:
        category = store.tax_categories[code]
        tax_amount = tax[code]
        deductible = int(tax_amount * DEEMED_PURCHASE_RATE)  # 切り捨て
        rate_lines.append(
            TaxRateLine(
                rate_percent=category.rate_percent,
                tax_code=code,
                taxable_sales_base=base[code],
                tax_amount=tax_amount,
                deductible_amount=deductible,
                payable_amount=tax_amount - deductible,
            )
        )
    return ConsumptionTax(
        fiscal_year=fiscal_year,
        business_type=BUSINESS_TYPE,
        deemed_purchase_rate=DEEMED_PURCHASE_RATE,
        tax_rates=rate_lines,
        total_tax_amount=sum(line.tax_amount for line in rate_lines),
        total_deductible_amount=sum(line.deductible_amount for line in rate_lines),
        total_payable_amount=sum(line.payable_amount for line in rate_lines),
    )


@router.get("/tax/consumption", response_model=ConsumptionTax)
def consumption_tax(fiscal_year: int) -> ConsumptionTax:
    """指定年度の消費税 (簡易課税) 集計を返す。

    Args:
        fiscal_year: 対象の会計年度。

    Returns:
        税率別および合計の消費税額・控除税額・納付税額。
    """
    return _calc_consumption_tax(fiscal_year)


@router.post("/tax/consumption/finalize", status_code=201)
def finalize_consumption_tax(fiscal_year: int) -> dict[str, object]:
    """消費税の納付額を確定し、未払計上の仕訳を計上する。

    仕訳: 借方 租税公課(601) / 貸方 未払消費税(330) を納付税額で計上する。

    Args:
        fiscal_year: 対象の会計年度。

    Returns:
        計上した仕訳と納付税額。

    Raises:
        HTTPException: 納付税額が0の場合 (400)。
    """
    summary = _calc_consumption_tax(fiscal_year)
    if summary.total_payable_amount <= 0:
        raise HTTPException(status_code=400, detail="納付税額がありません")
    lines = [
        JournalLine(
            side=Side.DEBIT, account_code=TAX_EXPENSE_CODE, amount=summary.total_payable_amount
        ),
        JournalLine(
            side=Side.CREDIT, account_code=TAX_PAYABLE_CODE, amount=summary.total_payable_amount
        ),
    ]
    entry = persist_entry(
        date_type(fiscal_year, 12, 31),
        f"消費税確定 {fiscal_year}年度",
        lines,
        source="tax-finalize",
    )
    return {"journal_entry": entry, "payable_amount": summary.total_payable_amount}
