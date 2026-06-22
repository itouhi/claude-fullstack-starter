"""Phase 3 (CSV取込・科目推測・ダッシュボード) のテスト。

由来: 全体基本設計 §6.3 / F-105, F-503/504, F-706。
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.account_suggester import suggest_account
from app.store import store

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_store() -> None:
    """各テスト前にストアを初期化する。"""
    store.reset()


def test_suggest_account_from_keywords() -> None:
    """摘要キーワードから相手科目を推測する (F-105)。"""
    assert suggest_account("○○電力 電気料金") == "602"  # 水道光熱費
    assert suggest_account("ﾌﾘｺﾐ手数料") == "613"  # 支払手数料
    assert suggest_account("Amazon 事務用品") == "608"  # 消耗品費
    assert suggest_account("謎の取引") is None


SBI_CSV = """日付,摘要,出金金額(円),入金金額(円),残高(円)
2026-01-10,振込手数料,330,,994670
2026-01-15,A社 売上入金,,100000,1094670
2026-01-20,謎の支払い,5000,,1089670
"""


def test_import_csv_creates_candidates_with_suggestions() -> None:
    """CSV取込が明細候補を生成し、相手科目を推測する (F-503)。"""
    res = client.post(
        "/api/imports/csv",
        json={"account_code": "102", "csv_text": SBI_CSV, "adapter": "sbi"},
    )
    assert res.status_code == 201
    batch = res.json()
    assert len(batch["transactions"]) == 3  # ヘッダ行は除外
    txns = batch["transactions"]
    assert txns[0]["payment"] == 330
    assert txns[0]["suggested_account_code"] == "613"  # 振込手数料
    assert txns[1]["receipt"] == 100000
    assert txns[1]["suggested_account_code"] == "500"  # 売上入金
    assert txns[2]["suggested_account_code"] is None  # 推測不可


def test_confirm_transaction_creates_journal() -> None:
    """取込明細の確定が複式仕訳を生成する (F-504)。入金は借方:口座。"""
    batch = client.post(
        "/api/imports/csv",
        json={"account_code": "102", "csv_text": SBI_CSV, "adapter": "sbi"},
    ).json()
    receipt_tx = next(t for t in batch["transactions"] if t["receipt"] > 0)

    res = client.post(
        f"/api/imports/{batch['id']}/transactions/{receipt_tx['id']}/confirm",
        json={},
    )
    assert res.status_code == 201
    entry = res.json()
    assert entry["source"] == "csv-import"
    lines = {line["side"]: line["account_code"] for line in entry["lines"]}
    assert lines["debit"] == "102"  # 預金が借方 (入金)
    assert lines["credit"] == "500"  # 推測科目 (売上高)

    # 明細が確定済みになる
    updated = client.get(f"/api/imports/{batch['id']}").json()
    confirmed = next(t for t in updated["transactions"] if t["id"] == receipt_tx["id"])
    assert confirmed["status"] == "confirmed"
    assert confirmed["journal_entry_id"] == entry["id"]


def test_confirm_without_counter_requires_account() -> None:
    """推測できない明細は相手科目未指定だと 422 になる。"""
    batch = client.post(
        "/api/imports/csv",
        json={"account_code": "102", "csv_text": SBI_CSV, "adapter": "sbi"},
    ).json()
    unknown_tx = next(t for t in batch["transactions"] if t["suggested_account_code"] is None)
    res = client.post(
        f"/api/imports/{batch['id']}/transactions/{unknown_tx['id']}/confirm", json={}
    )
    assert res.status_code == 422
    # 相手科目を指定すれば確定できる
    ok = client.post(
        f"/api/imports/{batch['id']}/transactions/{unknown_tx['id']}/confirm",
        json={"counter_code": "690"},
    )
    assert ok.status_code == 201


def test_skip_transaction() -> None:
    """取込明細をスキップできる。"""
    batch = client.post(
        "/api/imports/csv",
        json={"account_code": "102", "csv_text": SBI_CSV, "adapter": "sbi"},
    ).json()
    tx_id = batch["transactions"][0]["id"]
    res = client.post(f"/api/imports/{batch['id']}/transactions/{tx_id}/skip")
    assert res.status_code == 200
    assert res.json()["status"] == "skipped"


def test_dashboard_aggregates_key_metrics() -> None:
    """ダッシュボードが売上・利益・現預金・売掛金を集約する (F-706)。"""
    # 売掛計上 (売掛金 / 売上高 200,000)
    client.post(
        "/api/journal-entries",
        json={
            "date": "2026-03-01",
            "description": "役務提供",
            "lines": [
                {"side": "debit", "account_code": "135", "amount": 200000},
                {"side": "credit", "account_code": "500", "amount": 200000},
            ],
        },
    )
    # 現金経費 (消耗品費 / 現金 8,000)
    client.post(
        "/api/journal-entries",
        json={
            "date": "2026-03-05",
            "description": "消耗品",
            "lines": [
                {"side": "debit", "account_code": "608", "amount": 8000},
                {"side": "credit", "account_code": "101", "amount": 8000},
            ],
        },
    )
    dash = client.get("/api/reports/dashboard", params={"fiscal_year": 2026}).json()
    assert dash["revenue_total"] == 200000
    assert dash["net_income"] == 192000  # 200,000 - 8,000
    assert dash["cash_balance"] == -8000  # 現金が 8,000 減少
    assert dash["receivables_balance"] == 200000  # 売掛金残高 (未入金)
