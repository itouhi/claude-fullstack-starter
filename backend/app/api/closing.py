"""決算・青色申告決算書の API (M8 closing-tax)。

M6 (固定資産) と M7 (帳簿集計) の出力を読み取り専用で集約し、青色申告決算書
(損益計算書・貸借対照表・減価償却明細・月別売上) のデータを返す。

由来: 要件定義 F-802 / closing-tax 基本設計 §6 (青色申告決算書の集約設計)。
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.reports import (
    BalanceSheet,
    MonthlySales,
    ProfitAndLoss,
    balance_sheet,
    monthly_sales,
    profit_and_loss,
)
from app.domain.fixed_assets import AssetStatus
from app.services.depreciation import entry_for_year
from app.store import store

router = APIRouter()


class DepreciationDetail(BaseModel):
    """青色申告決算書「減価償却費の計算」の1行 (由来: F-602 / REQ-012)。"""

    asset_name: str
    acquisition_cost: int
    useful_life_years: int
    depreciation_amount: int  # 当期の事業按分後償却費 (減価償却費計上額)
    closing_book_value: int  # 期末帳簿価額 (未償却残高)


class BlueReturn(BaseModel):
    """青色申告決算書データ (由来: F-802 / closing-tax BD-102)。

    第1表(損益計算書)・第3表(貸借対照表・減価償却)・月別売上を集約する。
    """

    fiscal_year: int
    profit_and_loss: ProfitAndLoss
    balance_sheet: BalanceSheet
    monthly_sales: MonthlySales
    depreciation: list[DepreciationDetail]


def _depreciation_details(fiscal_year: int) -> list[DepreciationDetail]:
    """指定年度の固定資産ごとの減価償却明細を生成する。"""
    details: list[DepreciationDetail] = []
    for asset in sorted(store.fixed_assets.values(), key=lambda a: a.id):
        if asset.status == AssetStatus.DELETED:
            continue
        entry = entry_for_year(asset, fiscal_year)
        details.append(
            DepreciationDetail(
                asset_name=asset.name,
                acquisition_cost=asset.acquisition_cost,
                useful_life_years=asset.useful_life_years,
                depreciation_amount=entry.business_depreciation if entry else 0,
                closing_book_value=entry.closing_book_value if entry else asset.book_value,
            )
        )
    return details


@router.get("/closing/blue-return", response_model=BlueReturn)
def blue_return(fiscal_year: int) -> BlueReturn:
    """指定会計年度の青色申告決算書データを集約して返す。

    M7 の損益計算書・貸借対照表・月別売上と、M6 の固定資産から当年度の減価償却
    明細を組み合わせる。

    Args:
        fiscal_year: 対象の会計年度。

    Returns:
        損益計算書・貸借対照表・月別売上・減価償却明細を集約した青色申告決算書データ。
    """
    return BlueReturn(
        fiscal_year=fiscal_year,
        profit_and_loss=profit_and_loss(fiscal_year),
        balance_sheet=balance_sheet(fiscal_year),
        monthly_sales=monthly_sales(fiscal_year),
        depreciation=_depreciation_details(fiscal_year),
    )
