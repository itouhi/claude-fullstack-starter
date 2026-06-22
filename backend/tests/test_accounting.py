"""共通基盤 (勘定科目・仕訳・試算表) のテスト。

由来: 全体基本設計 §4 (共通データモデル) / F-101, F-103, F-201, F-703。
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import store

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_store() -> None:
    """各テスト前に仕訳をクリアし標準マスタへ戻す。"""
    store.reset()


def test_list_accounts_returns_standard_set() -> None:
    """勘定科目マスタが標準セットを表示順で返す。"""
    res = client.get("/api/accounts")
    assert res.status_code == 200
    accounts = res.json()
    assert any(a["code"] == "500" and a["name"] == "売上高" for a in accounts)
    orders = [a["order"] for a in accounts]
    assert orders == sorted(orders)


def test_list_tax_categories() -> None:
    """税区分マスタに課税売上10%が含まれる。"""
    res = client.get("/api/tax-categories")
    assert res.status_code == 200
    assert any(t["code"] == "T10" and t["rate_percent"] == 10 for t in res.json())


def test_create_balanced_journal_entry() -> None:
    """借方=貸方の仕訳を登録でき、会計年度が日付から決まる。"""
    payload = {
        "date": "2026-06-22",
        "description": "役務提供売上 (現金)",
        "lines": [
            {"side": "debit", "account_code": "101", "amount": 110000, "tax_code": "EX"},
            {
                "side": "credit",
                "account_code": "500",
                "amount": 110000,
                "tax_code": "T10",
                "tax_amount": 10000,
            },
        ],
    }
    res = client.post("/api/journal-entries", json=payload)
    assert res.status_code == 201
    body = res.json()
    assert body["id"] == 1
    assert body["fiscal_year"] == 2026
    assert body["status"] == "active"


def test_unbalanced_journal_entry_rejected() -> None:
    """借方と貸方が一致しない仕訳は 422 で拒否される。"""
    payload = {
        "date": "2026-06-22",
        "description": "不整合な仕訳",
        "lines": [
            {"side": "debit", "account_code": "101", "amount": 100000},
            {"side": "credit", "account_code": "500", "amount": 90000},
        ],
    }
    res = client.post("/api/journal-entries", json=payload)
    assert res.status_code == 422


def test_unknown_account_rejected() -> None:
    """存在しない勘定科目を参照する仕訳は 422 で拒否される。"""
    payload = {
        "date": "2026-06-22",
        "description": "未知科目",
        "lines": [
            {"side": "debit", "account_code": "999", "amount": 1000},
            {"side": "credit", "account_code": "500", "amount": 1000},
        ],
    }
    res = client.post("/api/journal-entries", json=payload)
    assert res.status_code == 422


def test_delete_is_logical_and_excluded_from_list() -> None:
    """論理削除した仕訳は一覧・試算表から除外される (物理削除しない)。"""
    payload = {
        "date": "2026-06-22",
        "description": "削除対象",
        "lines": [
            {"side": "debit", "account_code": "101", "amount": 5000},
            {"side": "credit", "account_code": "500", "amount": 5000},
        ],
    }
    created = client.post("/api/journal-entries", json=payload).json()
    res = client.delete(f"/api/journal-entries/{created['id']}")
    assert res.status_code == 200
    assert res.json()["status"] == "deleted"
    assert client.get("/api/journal-entries").json() == []


def test_trial_balance_is_balanced() -> None:
    """試算表の借方合計と貸方合計が一致し、残高が区分どおりに算出される。"""
    # 売上 (現金 110,000 / 売上高 110,000)
    client.post(
        "/api/journal-entries",
        json={
            "date": "2026-06-22",
            "description": "売上",
            "lines": [
                {"side": "debit", "account_code": "101", "amount": 110000},
                {"side": "credit", "account_code": "500", "amount": 110000},
            ],
        },
    )
    # 経費 (消耗品費 3,000 / 現金 3,000)
    client.post(
        "/api/journal-entries",
        json={
            "date": "2026-06-22",
            "description": "消耗品購入",
            "lines": [
                {"side": "debit", "account_code": "608", "amount": 3000},
                {"side": "credit", "account_code": "101", "amount": 3000},
            ],
        },
    )
    res = client.get("/api/reports/trial-balance")
    assert res.status_code == 200
    tb = res.json()
    assert tb["debit_total"] == tb["credit_total"]
    rows = {r["account_code"]: r for r in tb["rows"]}
    assert rows["101"]["balance"] == 107000  # 現金: 110,000 - 3,000
    assert rows["500"]["balance"] == 110000  # 売上高 (収益は貸方が正)
    assert rows["608"]["balance"] == 3000  # 消耗品費 (費用は借方が正)


def _seed_sales_and_expense() -> None:
    """売上 110,000 と経費 3,000 の2仕訳を登録する (PL/BS テスト用)。"""
    client.post(
        "/api/journal-entries",
        json={
            "date": "2026-06-22",
            "description": "売上",
            "lines": [
                {"side": "debit", "account_code": "101", "amount": 110000},
                {"side": "credit", "account_code": "500", "amount": 110000},
            ],
        },
    )
    client.post(
        "/api/journal-entries",
        json={
            "date": "2026-06-22",
            "description": "消耗品購入",
            "lines": [
                {"side": "debit", "account_code": "608", "amount": 3000},
                {"side": "credit", "account_code": "101", "amount": 3000},
            ],
        },
    )


def test_profit_and_loss() -> None:
    """損益計算書: 当期純利益 = 収益合計 − 費用合計。"""
    _seed_sales_and_expense()
    pl = client.get("/api/reports/pl").json()
    assert pl["total_revenue"] == 110000
    assert pl["total_expense"] == 3000
    assert pl["net_income"] == 107000


def test_balance_sheet_identity() -> None:
    """貸借対照表: 資産合計 = 負債合計 + 純資産合計 (当期純利益を含む)。"""
    _seed_sales_and_expense()
    bs = client.get("/api/reports/bs").json()
    assert bs["total_assets"] == 107000  # 現金 110,000 - 3,000
    assert bs["net_income"] == 107000  # 純資産に算入される当期純利益
    assert bs["total_assets"] == bs["total_liabilities"] + bs["total_equity"]


def test_cash_entry_receipt_creates_balanced_journal() -> None:
    """出納帳の入金簡易入力が 借方:現金/貸方:相手科目 の仕訳になる。"""
    res = client.post(
        "/api/cash-book/entries",
        json={
            "account_code": "101",
            "direction": "receipt",
            "counter_code": "500",
            "amount": 50000,
            "description": "現金売上",
            "date": "2026-06-22",
        },
    )
    assert res.status_code == 201
    entry = res.json()
    assert entry["source"] == "cash-book"
    debit = next(line for line in entry["lines"] if line["side"] == "debit")
    credit = next(line for line in entry["lines"] if line["side"] == "credit")
    assert debit["account_code"] == "101"  # 現金が借方 (入金)
    assert credit["account_code"] == "500"
    assert credit["tax_code"] == "T10"  # 相手科目の既定税区分を補完


def test_cash_entry_payment_direction() -> None:
    """出金簡易入力は 借方:相手科目/貸方:現金 になる。"""
    res = client.post(
        "/api/cash-book/entries",
        json={
            "account_code": "101",
            "direction": "payment",
            "counter_code": "608",
            "amount": 3000,
            "description": "消耗品を現金購入",
            "date": "2026-06-22",
        },
    )
    assert res.status_code == 201
    lines = {line["side"]: line["account_code"] for line in res.json()["lines"]}
    assert lines["debit"] == "608"  # 消耗品費が借方
    assert lines["credit"] == "101"  # 現金が貸方 (出金)


def test_cash_book_running_balance() -> None:
    """出納帳が入金・出金を時系列で集計し残高を積み上げる。"""
    client.post(
        "/api/cash-book/entries",
        json={
            "account_code": "101",
            "direction": "receipt",
            "counter_code": "500",
            "amount": 50000,
            "description": "売上",
            "date": "2026-06-20",
        },
    )
    client.post(
        "/api/cash-book/entries",
        json={
            "account_code": "101",
            "direction": "payment",
            "counter_code": "608",
            "amount": 3000,
            "description": "消耗品",
            "date": "2026-06-22",
        },
    )
    book = client.get("/api/cash-book/101").json()
    assert book["account_name"] == "現金"
    assert [r["receipt"] for r in book["rows"]] == [50000, 0]
    assert [r["payment"] for r in book["rows"]] == [0, 3000]
    assert [r["balance"] for r in book["rows"]] == [50000, 47000]
    assert book["closing_balance"] == 47000
    assert book["rows"][0]["counter_account"] == "売上高"


def test_cash_entry_rejects_non_asset_account() -> None:
    """口座に資産以外の科目を指定すると 422 で拒否される。"""
    res = client.post(
        "/api/cash-book/entries",
        json={
            "account_code": "500",
            "direction": "receipt",
            "counter_code": "101",
            "amount": 1000,
            "description": "x",
            "date": "2026-06-22",
        },
    )
    assert res.status_code == 422


def test_general_ledger_running_balance() -> None:
    """総勘定元帳が科目別に相手科目と繰越残高を返す。"""
    _seed_sales_and_expense()  # 現金: +110,000 then -3,000
    ledger = client.get("/api/reports/general-ledger", params={"account_code": "101"}).json()
    assert ledger["account_name"] == "現金"
    assert [r["running_balance"] for r in ledger["rows"]] == [110000, 107000]
    assert ledger["rows"][0]["counter_account"] == "売上高"
    assert ledger["closing_balance"] == 107000
