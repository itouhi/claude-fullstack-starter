# 個人事業主向け 会計システム ドキュメント索引

要件定義書 v1.0 を起点に、**全体基本設計 → 機能別 (要件・基本設計) → 実装** の順で開発する。
機能は「仕訳を作る側／読む側」に分離し、共通基盤の確立後はモジュールを並列開発する
(並列開発DAGは全体基本設計 §6 を参照)。

## 全体
- [00 全体基本設計書](./00-overall-basic-design.md) — アーキテクチャ・共通データモデル(複式簿記)・9モジュール分割・並列開発DAG・税計算ルール

## 機能モジュール (docs/accounting/<機能>/)
| M-ID | モジュール | ドキュメント | 担当 F-ID | Layer |
|------|-----------|------------|----------|-------|
| M1 | core-masters | (基盤: store.py / accounts.py に実装) | F-201〜205 | 0 |
| M2 | journal | (基盤: domain/journal.py / api/journal.py に実装) | F-101〜106 | 0 |
| M3 | [receivables](./receivables/README.md) | 要件 / 基本設計 | F-301,302 | 1 |
| M4 | [expenses](./expenses/README.md) | 要件 / 基本設計 | F-401〜403 | 1 |
| M5 | [cash-bank](./cash-bank/README.md) | 要件 / 基本設計 | F-501〜504 | 1 |
| M6 | [fixed-assets](./fixed-assets/README.md) | 要件 / 基本設計 | F-601〜603 | 1 |
| M7 | [reports](./reports/README.md) | 要件 / 基本設計 | F-701〜707 | 2 |
| M8 | [closing-tax](./closing-tax/README.md) | 要件 / 基本設計 | F-801〜804 | 3 |
| M9 | [data-io](./data-io/README.md) | 要件 / 基本設計 | F-901〜904 | 横断 |

## 実装状況 (Phase 1 完了)
記帳基盤 (Layer0) + 出納帳 (M5) + 基本帳簿 (M7) を実装し、ブラウザで動作確認済み
(簡易入力→仕訳→出納帳→総勘定元帳→試算表→PL→BS が一貫して整合)。

| 機能 | backend | frontend | テスト | 状態 |
|------|---------|----------|--------|------|
| 勘定科目・税区分マスタ (M1) | `app/api/accounts.py` / `app/store.py` | `services/accounting.ts` | ✓ | 実装済 |
| 仕訳エンジン (M2 F-101/103) | `app/domain/journal.py` / `app/api/journal.py` | `components/JournalEntryForm.vue` | ✓ | 実装済 (借貸検証・論理削除) |
| 出納帳・簡易入力 (M5 F-501/502/102) | `app/api/cash_book.py` | `components/CashBook.vue` | ✓ | 実装済 (入金/出金→複式仕訳) |
| 仕訳帳 (M7 F-701) | `app/api/journal.py` | `components/JournalList.vue` | ✓ | 実装済 |
| 総勘定元帳 (M7 F-702) | `app/api/reports.py` | `components/GeneralLedgerView.vue` | ✓ | 実装済 |
| 合計残高試算表 (M7 F-703) | `app/api/reports.py` | `components/TrialBalanceView.vue` | ✓ | 実装済 |
| 損益計算書 PL (M7 F-704) | `app/api/reports.py` | `components/ProfitAndLossView.vue` | ✓ | 実装済 |
| 貸借対照表 BS (M7 F-705) | `app/api/reports.py` | `components/BalanceSheetView.vue` | ✓ | 実装済 |

> backend テスト 17 件パス (ruff/mypy クリーン)。Phase 1 以外のモジュール (M3/M4/M6 と
> M5のCSV取込・M7のダッシュボード/月別売上・M8・M9) は基本設計まで完了。実装は並列開発DAGの Layer 順に進める。
