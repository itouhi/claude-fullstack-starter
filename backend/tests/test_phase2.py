"""Phase 2 (固定資産・減価償却・青色申告決算書) のテスト。

由来: 全体基本設計 §6.3 / F-601〜603, F-707, F-802 /
      fixed-assets 基本設計 §6 (数値例) / closing-tax 基本設計 §6。
"""

import pytest
from fastapi.testclient import TestClient

from app.domain.fixed_assets import FixedAsset
from app.main import app
from app.services.depreciation import depreciation_schedule
from app.store import now, store

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_store() -> None:
    """各テスト前にストアを初期化する。"""
    store.reset()


def _asset(**overrides: object) -> FixedAsset:
    """テスト用の固定資産を生成する。"""
    moment = now()
    defaults: dict[str, object] = {
        "id": 1,
        "name": "ノートPC",
        "acquisition_date": "2025-04-01",
        "acquisition_cost": 300000,
        "useful_life_years": 5,
        "business_use_ratio": 1.0,
        "is_small_amount_special": False,
        "book_value": 300000,
        "accumulated_depreciation": 0,
        "created_at": moment,
        "updated_at": moment,
    }
    defaults.update(overrides)
    return FixedAsset(**defaults)


def test_depreciation_schedule_straight_line_midyear() -> None:
    """定額法・期中取得の償却スケジュール (基本設計 §6.3 のルールに準拠)。

    取得価額300,000・耐用年数5年・2025年4月取得。初年度は月割9ヶ月で45,000、
    以後は満年60,000。期中取得のため未償却分が翌2030年度に残り、最終年度は
    備忘価額1円を残して14,999を償却する。
    """
    schedule = depreciation_schedule(_asset())
    amounts = {e.fiscal_year: e.depreciation_amount for e in schedule}
    assert amounts[2025] == 45000  # 月割 9ヶ月: 60,000 × 9/12
    assert amounts[2026] == 60000
    assert amounts[2027] == 60000
    assert amounts[2028] == 60000
    assert amounts[2029] == 60000
    assert amounts[2030] == 14999  # 残額 15,000 − 備忘1円
    assert schedule[-1].fiscal_year == 2030
    assert schedule[-1].closing_book_value == 1  # 備忘価額1円


def test_small_amount_special_immediate_depreciation() -> None:
    """少額特例は取得年度に全額即時償却 (備忘1円残し)。"""
    asset = _asset(acquisition_cost=150000, book_value=150000, is_small_amount_special=True)
    schedule = depreciation_schedule(asset)
    assert len(schedule) == 1
    assert schedule[0].depreciation_amount == 149999  # 150,000 - 1
    assert schedule[0].closing_book_value == 1


def test_household_apportionment_splits_lines() -> None:
    """家事按分ありは事業分(609)と家事分(事業主貸410)に按分される。"""
    asset = _asset(business_use_ratio=0.8)
    first = depreciation_schedule(asset)[0]  # 2025年度 45,000
    assert first.business_depreciation == 36000  # 45,000 × 0.8
    assert first.private_depreciation == 9000  # 残り
    assert first.business_depreciation + first.private_depreciation == first.depreciation_amount


def test_create_fixed_asset_and_post_depreciation() -> None:
    """固定資産を登録し、当期償却を仕訳計上できる (直接法)。"""
    created = client.post(
        "/api/fixed-assets",
        json={
            "name": "ノートPC",
            "acquisition_date": "2025-04-01",
            "acquisition_cost": 300000,
            "useful_life_years": 5,
        },
    )
    assert created.status_code == 201
    asset_id = created.json()["id"]

    posted = client.post(f"/api/fixed-assets/{asset_id}/depreciation", params={"fiscal_year": 2025})
    assert posted.status_code == 201
    entry = posted.json()
    lines = {line["side"]: line for line in entry["lines"]}
    assert lines["debit"]["account_code"] == "609"  # 減価償却費
    assert lines["debit"]["amount"] == 45000
    assert lines["credit"]["account_code"] == "150"  # 工具器具備品 (直接法)

    # 台帳が更新される
    asset = client.get("/api/fixed-assets").json()[0]
    assert asset["book_value"] == 255000  # 300,000 - 45,000
    assert asset["accumulated_depreciation"] == 45000


def test_post_depreciation_twice_is_rejected() -> None:
    """同一年度の二重償却計上は 409 で拒否される。"""
    created = client.post(
        "/api/fixed-assets",
        json={
            "name": "PC",
            "acquisition_date": "2025-04-01",
            "acquisition_cost": 300000,
            "useful_life_years": 5,
        },
    )
    asset_id = created.json()["id"]
    client.post(f"/api/fixed-assets/{asset_id}/depreciation", params={"fiscal_year": 2025})
    again = client.post(f"/api/fixed-assets/{asset_id}/depreciation", params={"fiscal_year": 2025})
    assert again.status_code == 409


def test_small_amount_special_requires_under_limit() -> None:
    """少額特例は取得価額30万円以上では適用できない (422)。"""
    res = client.post(
        "/api/fixed-assets",
        json={
            "name": "高額機器",
            "acquisition_date": "2025-04-01",
            "acquisition_cost": 300000,
            "useful_life_years": 5,
            "use_small_amount_special": True,
        },
    )
    assert res.status_code == 422


def test_monthly_sales_aggregates_by_month() -> None:
    """月別売上が売上高(500)を月別に集計する。"""
    for month, amount in [(1, 100000), (1, 50000), (3, 200000)]:
        client.post(
            "/api/journal-entries",
            json={
                "date": f"2026-0{month}-15",
                "description": "売上",
                "lines": [
                    {"side": "debit", "account_code": "101", "amount": amount},
                    {"side": "credit", "account_code": "500", "amount": amount},
                ],
            },
        )
    ms = client.get("/api/reports/monthly-sales", params={"fiscal_year": 2026}).json()
    by_month = {r["month"]: r["amount"] for r in ms["rows"]}
    assert by_month[1] == 150000
    assert by_month[3] == 200000
    assert by_month[2] == 0
    assert len(ms["rows"]) == 12
    assert ms["total"] == 350000


def test_blue_return_aggregates_statements() -> None:
    """青色申告決算書が PL/BS/月別売上/減価償却を集約して返す。"""
    # 売上を計上
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
    # 固定資産を登録し当期償却を計上
    asset_id = client.post(
        "/api/fixed-assets",
        json={
            "name": "ノートPC",
            "acquisition_date": "2025-04-01",
            "acquisition_cost": 300000,
            "useful_life_years": 5,
        },
    ).json()["id"]
    client.post(f"/api/fixed-assets/{asset_id}/depreciation", params={"fiscal_year": 2025})

    br = client.get("/api/closing/blue-return", params={"fiscal_year": 2025}).json()
    assert br["fiscal_year"] == 2025
    assert br["profit_and_loss"]["total_revenue"] == 500000
    # 減価償却費45,000 が費用に含まれ、当期純利益 = 500,000 - 45,000
    assert br["profit_and_loss"]["net_income"] == 455000
    assert br["monthly_sales"]["total"] == 500000
    assert len(br["depreciation"]) == 1
    assert br["depreciation"][0]["depreciation_amount"] == 45000
    assert br["depreciation"][0]["closing_book_value"] == 255000
