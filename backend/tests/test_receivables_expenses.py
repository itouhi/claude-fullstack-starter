"""M3 売上売掛・M4 経費の専用機能テスト。

由来: F-301/302 (売掛) / F-401/403 (経費) / receivables・expenses 基本設計。
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import store

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_store() -> None:
    """各テスト前にストアを初期化する。"""
    store.reset()


def test_sales_creates_receivable_with_internal_tax() -> None:
    """売上計上が 借方:売掛金(取引先) / 貸方:売上高 で内税を計算する。"""
    res = client.post(
        "/api/receivables/sales",
        json={
            "counterparty": "A社",
            "amount": 110000,
            "date": "2026-04-10",
            "description": "コンサル料",
        },
    )
    assert res.status_code == 201
    entry = res.json()
    debit = next(line for line in entry["lines"] if line["side"] == "debit")
    credit = next(line for line in entry["lines"] if line["side"] == "credit")
    assert debit["account_code"] == "135" and debit["sub_account"] == "A社"
    assert credit["account_code"] == "500"
    assert credit["tax_amount"] == 10000  # floor(110,000 × 10/110)


def test_receivable_outstanding_and_payment_clearing() -> None:
    """売上後は未入金が立ち、入金で消し込まれる。"""
    client.post(
        "/api/receivables/sales",
        json={"counterparty": "A社", "amount": 110000, "date": "2026-04-10", "description": "売上"},
    )
    client.post(
        "/api/receivables/sales",
        json={"counterparty": "B社", "amount": 55000, "date": "2026-04-12", "description": "売上"},
    )
    outstanding = client.get("/api/receivables/outstanding").json()
    balances = {r["counterparty"]: r["balance"] for r in outstanding}
    assert balances == {"A社": 110000, "B社": 55000}

    # A社から入金 → 消込
    client.post(
        "/api/receivables/payment",
        json={"counterparty": "A社", "amount": 110000, "date": "2026-05-01"},
    )
    after = {
        r["counterparty"]: r["balance"] for r in client.get("/api/receivables/outstanding").json()
    }
    assert "A社" not in after  # 残高0は一覧から消える
    assert after["B社"] == 55000


def test_expense_immediate_cash() -> None:
    """即時現金払いの経費が 借方:経費 / 貸方:現金 になり既定税区分を補完する。"""
    res = client.post(
        "/api/expenses",
        json={
            "expense_account_code": "604",
            "amount": 11000,
            "credit_account_code": "101",
            "description": "通信費",
            "date": "2026-04-15",
        },
    )
    assert res.status_code == 201
    entry = res.json()
    debit = next(line for line in entry["lines"] if line["side"] == "debit")
    assert debit["account_code"] == "604"
    assert debit["tax_code"] == "TP10"  # 既定税区分
    assert debit["tax_amount"] == 1000  # floor(11,000 × 10/110)


def test_expense_payable_and_clearing() -> None:
    """未払計上で未払金が立ち、支払で消し込まれる。"""
    client.post(
        "/api/expenses",
        json={
            "expense_account_code": "611",
            "amount": 50000,
            "credit_account_code": "305",
            "description": "外注費",
            "date": "2026-04-20",
            "counterparty": "C社",
        },
    )
    payables = client.get("/api/expenses/payables").json()
    assert {r["counterparty"]: r["balance"] for r in payables} == {"C社": 50000}

    client.post(
        "/api/expenses/payment",
        json={"counterparty": "C社", "amount": 50000, "date": "2026-05-10"},
    )
    assert client.get("/api/expenses/payables").json() == []


def test_expense_rejects_non_expense_account() -> None:
    """借方に費用以外を指定すると 422 になる。"""
    res = client.post(
        "/api/expenses",
        json={
            "expense_account_code": "101",
            "amount": 1000,
            "credit_account_code": "101",
            "description": "x",
            "date": "2026-04-20",
        },
    )
    assert res.status_code == 422
