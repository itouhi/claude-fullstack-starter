"""税込金額からの内税計算 (M3/M4 共通)。

税込経理のため、税込金額に含まれる消費税額を税区分の税率から逆算する。

由来: receivables 基本設計 §3.2 / expenses 基本設計 §3.2。
"""

from app.store import store


def internal_tax(amount: int, tax_code: str | None) -> int:
    """税込金額に含まれる消費税額を返す (円未満切り捨て)。

    Args:
        amount: 税込金額 (円)。
        tax_code: 税区分コード。課税 (税率>0) の場合のみ内税を計算する。

    Returns:
        内税額。非課税・対象外・未知の税区分は 0。
    """
    if tax_code is None:
        return 0
    category = store.tax_categories.get(tax_code)
    if category is None or category.rate_percent == 0:
        return 0
    rate = category.rate_percent
    return amount * rate // (100 + rate)  # floor(税込 × r / (100+r))
