"""勘定科目・税区分のドメインモデル (共通基盤 M1)。

由来: 要件定義 F-201 (勘定科目マスタ) / F-204 (税区分マスタ) / 全体基本設計 §4。
"""

from enum import StrEnum

from pydantic import BaseModel


class AccountType(StrEnum):
    """勘定科目の5区分 (複式簿記の基本分類)。"""

    ASSET = "asset"  # 資産
    LIABILITY = "liability"  # 負債
    EQUITY = "equity"  # 純資産
    REVENUE = "revenue"  # 収益
    EXPENSE = "expense"  # 費用


#: 借方残高が正となる区分 (資産・費用)。それ以外は貸方残高が正。
DEBIT_POSITIVE_TYPES: frozenset[AccountType] = frozenset({AccountType.ASSET, AccountType.EXPENSE})


class TaxKind(StrEnum):
    """税区分の種別。"""

    TAXABLE = "taxable"  # 課税 (標準税率)
    REDUCED = "reduced"  # 軽減課税 (8%)
    NON_TAXABLE = "non_taxable"  # 非課税
    EXEMPT = "exempt"  # 対象外 (不課税)


class TaxCategory(BaseModel):
    """税区分マスタ。

    課税/非課税/対象外と税率を保持する。簡易課税の事業区分 (サービス業=第五種)
    を `business_type` に持ち、消費税集計 (M8) で参照する。

    由来: F-204, 全体基本設計 §4.2。
    """

    code: str
    name: str
    kind: TaxKind
    rate_percent: int = 0  # 税率 (%)。10 / 8 / 0
    business_type: int | None = None  # 簡易課税の事業区分 (サービス業=5)


class Account(BaseModel):
    """勘定科目マスタ。

    由来: F-201。`default_tax_code` は仕訳入力時の既定税区分を提案するために用いる。
    """

    code: str
    name: str
    type: AccountType
    default_tax_code: str | None = None
    order: int = 0  # 表示順 (帳簿・試算表の並び)
