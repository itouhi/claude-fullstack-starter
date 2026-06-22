"""永続化 (SQLModel + SQLite) のスナップショット往復テスト。

由来: 要件定義 N-2 (データ消失防止) / add-persistence。
"""

from datetime import UTC, datetime

import pytest
from sqlmodel import Session, select

from app.db import (
    JournalEntryRow,
    get_engine,
    init_db,
    load_snapshot,
    save_snapshot,
)
from app.domain.journal import JournalEntry, JournalLine, Side
from app.store import AccountingStore


@pytest.fixture
def engine(tmp_path):  # type: ignore[no-untyped-def]
    """一時ファイルの SQLite エンジンを用意する (テスト間で隔離)。"""
    import app.db as db

    db._engine = None  # プロセス共有エンジンをリセット
    eng = get_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db(eng)
    yield eng
    db._engine = None


def _entry(entry_id: int) -> JournalEntry:
    """テスト用の仕訳を生成する。"""
    moment = datetime.now(UTC)
    return JournalEntry(
        id=entry_id,
        date="2026-04-01",
        description="売上",
        fiscal_year=2026,
        lines=[
            JournalLine(side=Side.DEBIT, account_code="101", amount=10000),
            JournalLine(side=Side.CREDIT, account_code="500", amount=10000),
        ],
        created_at=moment,
        updated_at=moment,
    )


def test_snapshot_roundtrip_preserves_journal(engine) -> None:  # type: ignore[no-untyped-def]
    """保存した仕訳が別ストアへ復元され、採番カウンタも引き継がれる。"""
    source = AccountingStore()
    entry = _entry(source.next_entry_id())
    source.journal_entries[entry.id] = entry
    source.carried_years.add(2025)
    save_snapshot(engine, source)

    # 別プロセス相当の新しいストアに読み込む
    target = AccountingStore()
    load_snapshot(engine, target)
    assert target.journal_entries[entry.id].description == "売上"
    assert target.journal_entries[entry.id].lines[0].amount == 10000
    assert target.carried_years == {2025}
    # カウンタが復元され、次の採番が衝突しない
    assert target.next_entry_id() == source._next_entry_id


def test_snapshot_is_full_replacement(engine) -> None:  # type: ignore[no-untyped-def]
    """スナップショットは全置換 (削除された仕訳が DB に残らない)。"""
    store_a = AccountingStore()
    e1 = _entry(store_a.next_entry_id())
    e2 = _entry(store_a.next_entry_id())
    store_a.journal_entries = {e1.id: e1, e2.id: e2}
    save_snapshot(engine, store_a)

    del store_a.journal_entries[e1.id]
    save_snapshot(engine, store_a)

    with Session(engine) as session:
        rows = list(session.exec(select(JournalEntryRow)))
    assert {r.id for r in rows} == {e2.id}
