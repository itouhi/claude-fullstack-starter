"""in-memory データストアと標準マスタの初期データ (共通基盤)。

将来 `add-persistence` スキルで SQLModel + DB に置き換える。リポジトリ相当の
単純な辞書ストアとして、仕訳・勘定科目・税区分を保持する。

由来: 全体基本設計 §1.2 (永続化層) / §8 (段階的導入)。
"""

from datetime import UTC, datetime

from app.domain.accounts import Account, AccountType, TaxCategory, TaxKind
from app.domain.journal import JournalEntry


def now() -> datetime:
    """現在時刻 (UTC) を返す。仕訳の登録/訂正日時に用いる。"""
    return datetime.now(UTC)


# 標準税区分セット (由来: F-204 / P-3, P-4)
STANDARD_TAX_CATEGORIES: list[TaxCategory] = [
    TaxCategory(
        code="T10", name="課税売上10%", kind=TaxKind.TAXABLE, rate_percent=10, business_type=5
    ),
    TaxCategory(
        code="T08", name="課税売上8%(軽減)", kind=TaxKind.REDUCED, rate_percent=8, business_type=5
    ),
    TaxCategory(code="TP10", name="課税仕入10%", kind=TaxKind.TAXABLE, rate_percent=10),
    TaxCategory(code="TP08", name="課税仕入8%(軽減)", kind=TaxKind.REDUCED, rate_percent=8),
    TaxCategory(code="NT", name="非課税", kind=TaxKind.NON_TAXABLE),
    TaxCategory(code="EX", name="対象外", kind=TaxKind.EXEMPT),
]


# 標準勘定科目セット (個人事業主・サービス業向け、由来: F-201 / 業務概要 2.1)
# 仕入・棚卸資産・売上原価は事業特性により対象外 (要件定義 第10章)。
STANDARD_ACCOUNTS: list[Account] = [
    # 資産
    Account(code="101", name="現金", type=AccountType.ASSET, order=10),
    Account(code="102", name="普通預金", type=AccountType.ASSET, order=20),
    Account(code="135", name="売掛金", type=AccountType.ASSET, order=30),
    Account(code="150", name="工具器具備品", type=AccountType.ASSET, order=40),
    Account(code="160", name="前払費用", type=AccountType.ASSET, order=50),
    # 負債
    Account(code="305", name="未払金", type=AccountType.LIABILITY, order=110),
    Account(code="320", name="預り金", type=AccountType.LIABILITY, order=120),
    Account(code="330", name="未払消費税", type=AccountType.LIABILITY, order=130),
    # 純資産
    Account(code="400", name="元入金", type=AccountType.EQUITY, order=210),
    Account(code="410", name="事業主貸", type=AccountType.EQUITY, order=220),
    Account(code="420", name="事業主借", type=AccountType.EQUITY, order=230),
    # 収益
    Account(code="500", name="売上高", type=AccountType.REVENUE, default_tax_code="T10", order=310),
    Account(code="510", name="雑収入", type=AccountType.REVENUE, default_tax_code="EX", order=320),
    # 費用
    Account(
        code="601", name="租税公課", type=AccountType.EXPENSE, default_tax_code="EX", order=410
    ),
    Account(
        code="602", name="水道光熱費", type=AccountType.EXPENSE, default_tax_code="TP10", order=420
    ),
    Account(
        code="603", name="旅費交通費", type=AccountType.EXPENSE, default_tax_code="TP10", order=430
    ),
    Account(
        code="604", name="通信費", type=AccountType.EXPENSE, default_tax_code="TP10", order=440
    ),
    Account(
        code="605", name="接待交際費", type=AccountType.EXPENSE, default_tax_code="TP10", order=450
    ),
    Account(
        code="606", name="損害保険料", type=AccountType.EXPENSE, default_tax_code="NT", order=460
    ),
    Account(
        code="607", name="修繕費", type=AccountType.EXPENSE, default_tax_code="TP10", order=470
    ),
    Account(
        code="608", name="消耗品費", type=AccountType.EXPENSE, default_tax_code="TP10", order=480
    ),
    Account(
        code="609", name="減価償却費", type=AccountType.EXPENSE, default_tax_code="EX", order=490
    ),
    Account(
        code="610", name="福利厚生費", type=AccountType.EXPENSE, default_tax_code="TP10", order=500
    ),
    Account(
        code="611", name="外注工賃", type=AccountType.EXPENSE, default_tax_code="TP10", order=510
    ),
    Account(
        code="612", name="地代家賃", type=AccountType.EXPENSE, default_tax_code="NT", order=520
    ),
    Account(
        code="613", name="支払手数料", type=AccountType.EXPENSE, default_tax_code="TP10", order=530
    ),
    Account(code="690", name="雑費", type=AccountType.EXPENSE, default_tax_code="TP10", order=590),
]


class AccountingStore:
    """会計データの in-memory ストア。

    プロセス内の単一インスタンス `store` を共有する。永続化は将来 DB へ移行。
    """

    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {a.code: a for a in STANDARD_ACCOUNTS}
        self.tax_categories: dict[str, TaxCategory] = {t.code: t for t in STANDARD_TAX_CATEGORIES}
        self.journal_entries: dict[int, JournalEntry] = {}
        self._next_entry_id = 1

    def next_entry_id(self) -> int:
        """仕訳 ID を採番する。"""
        entry_id = self._next_entry_id
        self._next_entry_id += 1
        return entry_id

    def reset(self) -> None:
        """テスト用に仕訳をクリアし、マスタを標準セットへ戻す。"""
        self.accounts = {a.code: a for a in STANDARD_ACCOUNTS}
        self.tax_categories = {t.code: t for t in STANDARD_TAX_CATEGORIES}
        self.journal_entries = {}
        self._next_entry_id = 1


#: プロセス共有のストアインスタンス
store = AccountingStore()
