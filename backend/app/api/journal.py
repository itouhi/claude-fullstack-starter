"""仕訳の API (M2 journal — 仕訳エンジン)。

すべての取引の入口。借方=貸方のバランス検証を経て仕訳ストアに登録する。

由来: 要件定義 F-101 (仕訳入力) / F-103 (修正・削除) / 全体基本設計 §5。
"""

from datetime import date as date_type

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from app.domain.journal import EntryStatus, JournalEntry, JournalLine
from app.store import now, store

router = APIRouter()


class JournalEntryCreate(BaseModel):
    """仕訳登録リクエスト (由来: F-101)。会計年度は日付から決定する。"""

    date: date_type
    description: str
    lines: list[JournalLine]
    source: str = "manual"


def _validate_master_refs(lines: list[JournalLine]) -> None:
    """明細が参照する勘定科目・税区分がマスタに存在するか検証する。"""
    for line in lines:
        if line.account_code not in store.accounts:
            raise HTTPException(status_code=422, detail=f"未知の勘定科目: {line.account_code}")
        if line.tax_code is not None and line.tax_code not in store.tax_categories:
            raise HTTPException(status_code=422, detail=f"未知の税区分: {line.tax_code}")


def persist_entry(
    entry_date: date_type, description: str, lines: list[JournalLine], source: str
) -> JournalEntry:
    """明細を検証して仕訳を生成・登録する共通ヘルパー。

    仕訳API と出納帳簡易入力 (M5) など、仕訳を生成する全機能が共有する登録口。
    マスタ参照と借貸バランスを検証し、不正なら HTTPException(422) を送出する。

    Args:
        entry_date: 仕訳日付。会計年度は年から決定する。
        description: 摘要。
        lines: 仕訳明細。
        source: 仕訳の由来 (manual / cash-book など)。

    Returns:
        採番・登録された有効な仕訳。

    Raises:
        HTTPException: 参照マスタが無い、または借貸が一致しない場合 (422)。
    """
    _validate_master_refs(lines)
    moment = now()
    try:
        entry = JournalEntry(
            id=store.next_entry_id(),
            date=entry_date,
            description=description,
            fiscal_year=entry_date.year,
            lines=lines,
            source=source,
            created_at=moment,
            updated_at=moment,
        )
    except ValidationError as exc:
        # 借貸不一致など不変条件違反は 422 で返す
        messages = "; ".join(e["msg"] for e in exc.errors())
        raise HTTPException(status_code=422, detail=messages) from exc
    store.journal_entries[entry.id] = entry
    return entry


@router.get("/journal-entries", response_model=list[JournalEntry])
def list_journal_entries(fiscal_year: int | None = None) -> list[JournalEntry]:
    """仕訳を日付順で返す。論理削除済みは除外する。

    Args:
        fiscal_year: 指定するとその会計年度の仕訳のみを返す。

    Returns:
        日付・ID 昇順の有効な仕訳一覧。
    """
    entries = [
        e
        for e in store.journal_entries.values()
        if e.status != EntryStatus.DELETED and (fiscal_year is None or e.fiscal_year == fiscal_year)
    ]
    return sorted(entries, key=lambda e: (e.date, e.id))


@router.post("/journal-entries", response_model=JournalEntry, status_code=201)
def create_journal_entry(payload: JournalEntryCreate) -> JournalEntry:
    """仕訳を登録する。借方=貸方のバランスを検証する。

    Args:
        payload: 日付・摘要・明細を含む登録リクエスト。

    Returns:
        採番された有効な仕訳。

    Raises:
        HTTPException: 参照マスタが無い、または借貸が一致しない場合 (422)。
    """
    return persist_entry(payload.date, payload.description, payload.lines, payload.source)


@router.delete("/journal-entries/{entry_id}", response_model=JournalEntry)
def delete_journal_entry(entry_id: int) -> JournalEntry:
    """仕訳を論理削除する (物理削除しない、由来: F-103 / N-7)。

    Args:
        entry_id: 対象の仕訳 ID。

    Returns:
        論理削除後の仕訳。

    Raises:
        HTTPException: 仕訳が存在しない場合 (404)。
    """
    entry = store.journal_entries.get(entry_id)
    if entry is None or entry.status == EntryStatus.DELETED:
        raise HTTPException(status_code=404, detail="仕訳が見つかりません")
    updated = entry.model_copy(update={"status": EntryStatus.DELETED, "updated_at": now()})
    store.journal_entries[entry_id] = updated
    return updated
