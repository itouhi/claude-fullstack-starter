"""永続化層 (SQLModel + SQLite) — in-memory ストアの DB バックアップ。

`DATABASE_URL` が設定されている場合のみ有効。各エンティティを1テーブルに保存し、
ドメインモデルの JSON を payload 列に格納する。アプリ起動時に DB から in-memory
ストアへ読み込み、更新系リクエストの後にスナップショットを書き戻すことで、
プロセス再起動後もデータが失われないようにする (要件 N-2)。

> 方針: スキーマはマイグレーション (Alembic) で管理する。本モジュールの
> `create_all` は開発時の SQLite ファイル用の補助 (本番では alembic upgrade head)。

由来: add-persistence スキル / 全体基本設計 §1.2, §8。
"""

from __future__ import annotations

import json

from sqlalchemy import Engine
from sqlmodel import Field, Session, SQLModel, create_engine, delete, select

from app.domain.fixed_assets import FixedAsset
from app.domain.imports import ImportBatch
from app.domain.journal import JournalEntry
from app.domain.voucher import Voucher


class JournalEntryRow(SQLModel, table=True):
    """仕訳の永続化行 (payload に JournalEntry の JSON)。"""

    __tablename__ = "journal_entry"
    id: int = Field(primary_key=True)
    fiscal_year: int = Field(index=True)
    payload: str


class FixedAssetRow(SQLModel, table=True):
    """固定資産の永続化行。"""

    __tablename__ = "fixed_asset"
    id: int = Field(primary_key=True)
    payload: str


class VoucherRow(SQLModel, table=True):
    """証憑の永続化行 (電帳法の検索キーを列として持つ)。"""

    __tablename__ = "voucher"
    id: int = Field(primary_key=True)
    transaction_date: str = Field(index=True)
    amount: int = Field(index=True)
    counterparty: str = Field(index=True)
    payload: str


class ImportBatchRow(SQLModel, table=True):
    """CSV 取込バッチの永続化行。"""

    __tablename__ = "import_batch"
    id: int = Field(primary_key=True)
    payload: str


class MetaRow(SQLModel, table=True):
    """採番カウンタ・繰越済年度などの内部状態。"""

    __tablename__ = "meta"
    key: str = Field(primary_key=True)
    value: str


_engine: Engine | None = None


def get_engine(database_url: str) -> Engine:
    """プロセス共有の DB エンジンを返す (初回に生成)。"""
    global _engine
    if _engine is None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        _engine = create_engine(database_url, connect_args=connect_args)
    return _engine


def init_db(engine: Engine) -> None:
    """テーブルを作成する (開発用。本番は alembic upgrade head)。"""
    SQLModel.metadata.create_all(engine)


def save_snapshot(engine: Engine, store: object) -> None:
    """in-memory ストアの全内容を DB へ書き戻す (全置換)。"""
    from app.store import AccountingStore

    assert isinstance(store, AccountingStore)
    with Session(engine) as session:
        for table in (JournalEntryRow, FixedAssetRow, VoucherRow, ImportBatchRow, MetaRow):
            session.exec(delete(table))  # type: ignore[arg-type, call-overload]
        for entry in store.journal_entries.values():
            session.add(
                JournalEntryRow(
                    id=entry.id, fiscal_year=entry.fiscal_year, payload=entry.model_dump_json()
                )
            )
        for asset in store.fixed_assets.values():
            session.add(FixedAssetRow(id=asset.id, payload=asset.model_dump_json()))
        for voucher in store.vouchers.values():
            session.add(
                VoucherRow(
                    id=voucher.id,
                    transaction_date=voucher.transaction_date.isoformat(),
                    amount=voucher.amount,
                    counterparty=voucher.counterparty,
                    payload=voucher.model_dump_json(),
                )
            )
        for batch in store.import_batches.values():
            session.add(ImportBatchRow(id=batch.id, payload=batch.model_dump_json()))
        meta = {
            "next_entry_id": store._next_entry_id,
            "next_asset_id": store._next_asset_id,
            "next_batch_id": store._next_batch_id,
            "next_tx_id": store._next_tx_id,
            "next_voucher_id": store._next_voucher_id,
            "carried_years": sorted(store.carried_years),
        }
        session.add(MetaRow(key="state", value=json.dumps(meta)))
        session.commit()


def load_snapshot(engine: Engine, store: object) -> None:
    """DB の内容を in-memory ストアへ読み込む (起動時)。"""
    from app.store import AccountingStore

    assert isinstance(store, AccountingStore)
    with Session(engine) as session:
        store.journal_entries = {
            row.id: JournalEntry.model_validate_json(row.payload)
            for row in session.exec(select(JournalEntryRow))
        }
        store.fixed_assets = {
            row.id: FixedAsset.model_validate_json(row.payload)
            for row in session.exec(select(FixedAssetRow))
        }
        store.vouchers = {
            row.id: Voucher.model_validate_json(row.payload)
            for row in session.exec(select(VoucherRow))
        }
        store.import_batches = {
            row.id: ImportBatch.model_validate_json(row.payload)
            for row in session.exec(select(ImportBatchRow))
        }
        meta_row = session.exec(select(MetaRow).where(MetaRow.key == "state")).first()
        if meta_row is not None:
            meta = json.loads(meta_row.value)
            store._next_entry_id = meta["next_entry_id"]
            store._next_asset_id = meta["next_asset_id"]
            store._next_batch_id = meta["next_batch_id"]
            store._next_tx_id = meta["next_tx_id"]
            store._next_voucher_id = meta["next_voucher_id"]
            store.carried_years = set(meta["carried_years"])
