"""固定資産のドメインモデル (M6 fixed-assets)。

由来: 要件定義 F-601〜603 / 全体基本設計 §4 / fixed-assets 基本設計 §3。
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DepreciationMethod(StrEnum):
    """償却方法 (現在は定額法のみ)。"""

    STRAIGHT_LINE = "straight_line"  # 定額法


class AssetStatus(StrEnum):
    """固定資産の状態 (物理削除しない論理管理)。"""

    ACTIVE = "active"  # 償却中
    FULLY_DEPRECIATED = "fully_depreciated"  # 償却済 (備忘価額1円)
    DELETED = "deleted"  # 論理削除


class FixedAsset(BaseModel):
    """固定資産台帳のレコード (由来: F-601 / 基本設計 BD-005)。

    金額は円単位の整数。`book_value` (未償却残高) と `accumulated_depreciation`
    (償却累計) は償却計上のたびに更新される。
    """

    id: int
    name: str
    acquisition_date: date
    acquisition_cost: int = Field(gt=0)
    useful_life_years: int = Field(ge=1)
    depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE
    business_use_ratio: float = Field(default=1.0, gt=0, le=1.0)  # 事業専用割合
    is_small_amount_special: bool = False  # 少額特例 (<30万円・青色)
    book_value: int  # 未償却残高
    accumulated_depreciation: int = 0  # 償却累計
    description: str | None = None
    status: AssetStatus = AssetStatus.ACTIVE
    depreciated_years: list[int] = Field(default_factory=list)  # 償却計上済の年度
    created_at: datetime
    updated_at: datetime


class DepreciationEntry(BaseModel):
    """償却スケジュールの1行 (計算結果の値オブジェクト、由来: BD-006)。"""

    fiscal_year: int
    opening_book_value: int  # 期首未償却残高
    depreciation_amount: int  # 当期償却費 (貸方 工具器具備品の計上額 = 事業分+家事分)
    business_depreciation: int  # 借方 減価償却費609 (事業按分後)
    private_depreciation: int  # 借方 事業主貸410 (家事按分分)
    closing_book_value: int  # 期末未償却残高
