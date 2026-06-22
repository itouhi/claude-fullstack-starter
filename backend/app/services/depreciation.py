"""減価償却の計算ロジック (M6 — 純関数)。

定額法・期中取得の月割・最終年度の備忘価額1円残し・少額特例・家事按分を扱う。
入力が同じなら結果が必ず同一になる純関数として実装する (計算確定性)。

由来: 要件定義 F-602/603 / fixed-assets 基本設計 §6。
"""

from app.domain.fixed_assets import DepreciationEntry, FixedAsset
from app.domain.journal import JournalLine, Side

# 減価償却の勘定科目コード
ACCUMULATED_ASSET_CODE = "150"  # 工具器具備品 (直接法で減額)
DEPRECIATION_EXPENSE_CODE = "609"  # 減価償却費
OWNER_DRAWING_CODE = "410"  # 事業主貸 (家事按分分の振替先)


def _split_by_ratio(amount: int, business_use_ratio: float) -> tuple[int, int]:
    """償却費を事業分・家事分に按分する (事業分は切り捨て)。

    Returns:
        (事業按分後償却費, 家事按分分)。合計は元の amount に一致する。
    """
    business = int(amount * business_use_ratio)  # 切り捨て
    private = amount - business
    return business, private


def depreciation_schedule(asset: FixedAsset) -> list[DepreciationEntry]:
    """取得価額・耐用年数・取得日から年度別の償却スケジュールを算出する。

    定額法。取得年度は取得月から期末までの月割。最終年度は備忘価額1円を残す。
    少額特例は取得年度に全額即時償却する。

    Args:
        asset: 対象の固定資産。

    Returns:
        取得年度から償却完了年度までの `DepreciationEntry` の一覧。
    """
    acq_year = asset.acquisition_date.year
    acq_month = asset.acquisition_date.month
    book = asset.acquisition_cost

    if asset.is_small_amount_special:
        # 少額特例: 取得年度に取得価額 − 1 を即時償却 (備忘1円残し)
        amount = asset.acquisition_cost - 1
        business, private = _split_by_ratio(amount, asset.business_use_ratio)
        return [
            DepreciationEntry(
                fiscal_year=acq_year,
                opening_book_value=book,
                depreciation_amount=amount,
                business_depreciation=business,
                private_depreciation=private,
                closing_book_value=book - amount,
            )
        ]

    annual = asset.acquisition_cost // asset.useful_life_years  # 円未満切り捨て
    entries: list[DepreciationEntry] = []
    year = acq_year
    # 安全上限: 耐用年数 + 数年で必ず終了する
    max_year = acq_year + asset.useful_life_years + 2
    while book > 1 and year <= max_year:
        if year == acq_year:
            months = 12 - acq_month + 1  # 取得月から期末まで
            amount = annual * months // 12
        else:
            amount = annual
        if book - amount <= 1:
            amount = book - 1  # 最終年度: 備忘価額1円を残す
        if amount <= 0:
            break
        business, private = _split_by_ratio(amount, asset.business_use_ratio)
        entries.append(
            DepreciationEntry(
                fiscal_year=year,
                opening_book_value=book,
                depreciation_amount=amount,
                business_depreciation=business,
                private_depreciation=private,
                closing_book_value=book - amount,
            )
        )
        book -= amount
        year += 1
    return entries


def entry_for_year(asset: FixedAsset, fiscal_year: int) -> DepreciationEntry | None:
    """指定年度の償却スケジュール行を返す (なければ None)。"""
    for entry in depreciation_schedule(asset):
        if entry.fiscal_year == fiscal_year:
            return entry
    return None


def depreciation_journal_lines(entry: DepreciationEntry) -> list[JournalLine]:
    """償却スケジュール行から減価償却仕訳の明細を生成する (直接法)。

    家事按分なし → 借方:減価償却費 / 貸方:工具器具備品。
    家事按分あり → 借方:減価償却費(事業分) + 事業主貸(家事分) / 貸方:工具器具備品。

    Args:
        entry: 対象年度の償却スケジュール行。

    Returns:
        借貸が一致する仕訳明細の一覧。
    """
    lines: list[JournalLine] = []
    if entry.business_depreciation > 0:
        lines.append(
            JournalLine(
                side=Side.DEBIT,
                account_code=DEPRECIATION_EXPENSE_CODE,
                amount=entry.business_depreciation,
            )
        )
    if entry.private_depreciation > 0:
        lines.append(
            JournalLine(
                side=Side.DEBIT,
                account_code=OWNER_DRAWING_CODE,
                amount=entry.private_depreciation,
            )
        )
    lines.append(
        JournalLine(
            side=Side.CREDIT,
            account_code=ACCUMULATED_ASSET_CODE,
            amount=entry.depreciation_amount,
        )
    )
    return lines
