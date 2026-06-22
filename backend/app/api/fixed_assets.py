"""固定資産・減価償却の API (M6 fixed-assets)。

固定資産台帳を管理し、減価償却スケジュールの算出と当期償却の仕訳計上を行う。
償却仕訳は決算整理の一部として M8 (closing-tax) からも利用される。

由来: 要件定義 F-601/602/603 / fixed-assets 基本設計 §4。
"""

from datetime import date as date_type

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.journal import persist_entry
from app.domain.fixed_assets import (
    AssetStatus,
    DepreciationEntry,
    DepreciationMethod,
    FixedAsset,
)
from app.domain.journal import JournalEntry
from app.services.depreciation import depreciation_schedule, entry_for_year
from app.store import now, store

router = APIRouter()

# 少額減価償却資産特例の上限額 (30万円未満、青色申告)
SMALL_AMOUNT_LIMIT = 300_000


class FixedAssetCreate(BaseModel):
    """固定資産の登録リクエスト (由来: F-601 / BD-102)。"""

    name: str
    acquisition_date: date_type
    acquisition_cost: int = Field(gt=0)
    useful_life_years: int = Field(ge=1)
    business_use_ratio: float = Field(default=1.0, gt=0, le=1.0)
    use_small_amount_special: bool = False  # 少額特例を適用するか
    description: str | None = None


@router.get("/fixed-assets", response_model=list[FixedAsset])
def list_fixed_assets() -> list[FixedAsset]:
    """固定資産台帳の一覧を返す (論理削除済みを除く)。

    Returns:
        ID 昇順の固定資産一覧。
    """
    assets = [a for a in store.fixed_assets.values() if a.status != AssetStatus.DELETED]
    return sorted(assets, key=lambda a: a.id)


@router.post("/fixed-assets", response_model=FixedAsset, status_code=201)
def create_fixed_asset(payload: FixedAssetCreate) -> FixedAsset:
    """固定資産を登録する。少額特例の適用可否を判定する。

    Args:
        payload: 資産名・取得日・取得価額・耐用年数・事業専用割合など。

    Returns:
        採番・登録された固定資産。

    Raises:
        HTTPException: 少額特例を要求したが取得価額が30万円以上の場合 (422)。
    """
    is_special = payload.use_small_amount_special
    if is_special and payload.acquisition_cost >= SMALL_AMOUNT_LIMIT:
        raise HTTPException(
            status_code=422,
            detail="少額特例は取得価額30万円未満が条件です",
        )
    moment = now()
    asset = FixedAsset(
        id=store.next_asset_id(),
        name=payload.name,
        acquisition_date=payload.acquisition_date,
        acquisition_cost=payload.acquisition_cost,
        useful_life_years=payload.useful_life_years,
        depreciation_method=DepreciationMethod.STRAIGHT_LINE,
        business_use_ratio=payload.business_use_ratio,
        is_small_amount_special=is_special,
        book_value=payload.acquisition_cost,
        accumulated_depreciation=0,
        description=payload.description,
        created_at=moment,
        updated_at=moment,
    )
    store.fixed_assets[asset.id] = asset
    return asset


def _get_active_asset(asset_id: int) -> FixedAsset:
    """論理削除されていない固定資産を取得する (なければ 404)。"""
    asset = store.fixed_assets.get(asset_id)
    if asset is None or asset.status == AssetStatus.DELETED:
        raise HTTPException(status_code=404, detail="固定資産が見つかりません")
    return asset


@router.get(
    "/fixed-assets/{asset_id}/depreciation-schedule", response_model=list[DepreciationEntry]
)
def depreciation_schedule_of(asset_id: int) -> list[DepreciationEntry]:
    """固定資産の年度別償却予定表を返す。

    Args:
        asset_id: 対象の固定資産 ID。

    Returns:
        取得年度から償却完了までの償却スケジュール。
    """
    return depreciation_schedule(_get_active_asset(asset_id))


@router.post("/fixed-assets/{asset_id}/depreciation", response_model=JournalEntry, status_code=201)
def post_depreciation(asset_id: int, fiscal_year: int) -> JournalEntry:
    """指定年度の減価償却を仕訳計上し、未償却残高を更新する。

    Args:
        asset_id: 対象の固定資産 ID。
        fiscal_year: 償却を計上する会計年度。

    Returns:
        計上された減価償却仕訳。

    Raises:
        HTTPException: 当年度に償却がない (400)、または既に計上済み (409) の場合。
    """
    from app.services.depreciation import depreciation_journal_lines

    asset = _get_active_asset(asset_id)
    if fiscal_year in asset.depreciated_years:
        raise HTTPException(status_code=409, detail=f"{fiscal_year}年度は既に償却計上済みです")
    entry = entry_for_year(asset, fiscal_year)
    if entry is None:
        raise HTTPException(status_code=400, detail=f"{fiscal_year}年度に計上する償却はありません")

    lines = depreciation_journal_lines(entry)
    description = f"{asset.name} {fiscal_year}年度減価償却"
    journal = persist_entry(
        date_type(fiscal_year, 12, 31), description, lines, source="depreciation"
    )

    # 台帳を更新 (未償却残高・償却累計・償却済年度)
    new_status = AssetStatus.FULLY_DEPRECIATED if entry.closing_book_value <= 1 else asset.status
    updated = asset.model_copy(
        update={
            "book_value": entry.closing_book_value,
            "accumulated_depreciation": asset.accumulated_depreciation + entry.depreciation_amount,
            "depreciated_years": [*asset.depreciated_years, fiscal_year],
            "status": new_status,
            "updated_at": now(),
        }
    )
    store.fixed_assets[asset_id] = updated
    return journal
