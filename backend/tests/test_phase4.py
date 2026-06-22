"""Phase 4 (消費税・証憑・エクスポート・年度繰越) のテスト。

由来: 全体基本設計 §6.3 / F-804, F-402, F-902, F-904。
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


def _post_sale(amount: int, tax_amount: int, year: str = "2025") -> None:
    """税込売上 (現金/売上高) を計上する。"""
    client.post(
        "/api/journal-entries",
        json={
            "date": f"{year}-05-10",
            "description": "課税売上",
            "lines": [
                {"side": "debit", "account_code": "101", "amount": amount},
                {
                    "side": "credit",
                    "account_code": "500",
                    "amount": amount,
                    "tax_code": "T10",
                    "tax_amount": tax_amount,
                },
            ],
        },
    )


def test_consumption_tax_simplified() -> None:
    """簡易課税: 納付税額 = 消費税額 − 消費税額×みなし仕入率50% (F-804)。"""
    # 税込 5,500,000 (税抜 5,000,000 + 消費税 500,000)
    _post_sale(5500000, 500000)
    res = client.get("/api/tax/consumption", params={"fiscal_year": 2025}).json()
    assert res["deemed_purchase_rate"] == 0.5
    assert res["total_tax_amount"] == 500000
    assert res["total_deductible_amount"] == 250000  # × 50%
    assert res["total_payable_amount"] == 250000
    t10 = next(r for r in res["tax_rates"] if r["tax_code"] == "T10")
    assert t10["taxable_sales_base"] == 5000000  # 税抜


def test_consumption_tax_finalize_creates_journal() -> None:
    """消費税確定が 借方:租税公課 / 貸方:未払消費税 の仕訳を計上する。"""
    _post_sale(5500000, 500000)
    res = client.post("/api/tax/consumption/finalize", params={"fiscal_year": 2025})
    assert res.status_code == 201
    body = res.json()
    assert body["payable_amount"] == 250000
    lines = {line["side"]: line["account_code"] for line in body["journal_entry"]["lines"]}
    assert lines["debit"] == "601"  # 租税公課
    assert lines["credit"] == "330"  # 未払消費税


def test_voucher_save_and_search_by_three_keys() -> None:
    """証憑を保存し、電帳法の3キー (取引日・金額・取引先) で検索できる (F-402)。"""
    client.post(
        "/api/vouchers",
        json={
            "transaction_date": "2025-03-15",
            "amount": 33000,
            "counterparty": "ABC商事",
            "file_name": "receipt1.pdf",
        },
    )
    client.post(
        "/api/vouchers",
        json={
            "transaction_date": "2025-07-20",
            "amount": 5000,
            "counterparty": "XYZ書店",
            "file_name": "receipt2.pdf",
        },
    )
    # 取引先で検索
    by_party = client.get("/api/vouchers", params={"counterparty": "ABC"}).json()
    assert len(by_party) == 1
    assert by_party[0]["amount"] == 33000
    # 金額で検索
    by_amount = client.get("/api/vouchers", params={"amount": 5000}).json()
    assert len(by_amount) == 1
    # 取引日範囲で検索
    by_date = client.get(
        "/api/vouchers", params={"date_from": "2025-06-01", "date_to": "2025-12-31"}
    ).json()
    assert len(by_date) == 1
    assert by_date[0]["counterparty"] == "XYZ書店"


def test_voucher_rejects_unknown_journal() -> None:
    """存在しない仕訳への紐付けは 422 で拒否される。"""
    res = client.post(
        "/api/vouchers",
        json={
            "transaction_date": "2025-03-15",
            "amount": 1000,
            "counterparty": "X",
            "file_name": "a.pdf",
            "journal_entry_id": 999,
        },
    )
    assert res.status_code == 422


def test_export_journal_csv() -> None:
    """仕訳帳を CSV でエクスポートできる (F-902)。"""
    _post_sale(110000, 10000)
    res = client.get("/api/export/journal", params={"fiscal_year": 2025})
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    text = res.content.decode("utf-8-sig")
    assert "日付,摘要,借貸,勘定科目,金額,税区分" in text
    assert "売上高" in text


def test_export_pdf_not_implemented() -> None:
    """PDF 出力は 501 を返す。"""
    res = client.get("/api/export/pl", params={"format": "pdf"})
    assert res.status_code == 501


def test_export_unknown_report() -> None:
    """未知のレポート名は 404 を返す。"""
    res = client.get("/api/export/unknown")
    assert res.status_code == 404


def test_year_end_carry_forward() -> None:
    """年度繰越が期首振替仕訳を生成し、損益を元入金へ集約する (F-904)。"""
    # 売上 (現金 500,000 / 売上高 500,000)
    client.post(
        "/api/journal-entries",
        json={
            "date": "2025-05-10",
            "description": "売上",
            "lines": [
                {"side": "debit", "account_code": "101", "amount": 500000},
                {"side": "credit", "account_code": "500", "amount": 500000},
            ],
        },
    )
    # 経費 (消耗品費 80,000 / 現金 80,000)
    client.post(
        "/api/journal-entries",
        json={
            "date": "2025-06-01",
            "description": "経費",
            "lines": [
                {"side": "debit", "account_code": "608", "amount": 80000},
                {"side": "credit", "account_code": "101", "amount": 80000},
            ],
        },
    )
    # プレビュー: 現金残高 420,000、当期純利益 420,000、翌期首元入金 420,000
    preview = client.get("/api/year-end/carry-forward/preview", params={"fiscal_year": 2025}).json()
    assert preview["net_income"] == 420000
    assert preview["opening_capital_next"] == 420000

    # 実行: 翌期 (2026) の期首振替仕訳が生成される
    res = client.post("/api/year-end/carry-forward", params={"fiscal_year": 2025})
    assert res.status_code == 201
    entry = res.json()["opening_entry"]
    assert entry["fiscal_year"] == 2026
    lines = {line["account_code"]: line for line in entry["lines"]}
    assert lines["101"]["side"] == "debit" and lines["101"]["amount"] == 420000  # 現金繰越
    assert lines["400"]["side"] == "credit" and lines["400"]["amount"] == 420000  # 元入金

    # 二重繰越は 409
    again = client.post("/api/year-end/carry-forward", params={"fiscal_year": 2025})
    assert again.status_code == 409


def test_year_end_opening_reflected_in_next_year_bs() -> None:
    """繰越後、翌期の貸借対照表が期首残高を反映する。"""
    client.post(
        "/api/journal-entries",
        json={
            "date": "2025-05-10",
            "description": "売上",
            "lines": [
                {"side": "debit", "account_code": "101", "amount": 300000},
                {"side": "credit", "account_code": "500", "amount": 300000},
            ],
        },
    )
    client.post("/api/year-end/carry-forward", params={"fiscal_year": 2025})
    bs = client.get("/api/reports/bs", params={"fiscal_year": 2026}).json()
    assert bs["total_assets"] == 300000  # 現金が繰り越されている
    assert bs["total_assets"] == bs["total_liabilities"] + bs["total_equity"]
