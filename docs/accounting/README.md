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

### Phase 2 完了 (決算機能)
固定資産・減価償却 (M6) と青色申告決算書 (M8) を実装。減価償却の計算 (定額法/月割/
備忘1円/少額特例/家事按分) はブラウザで動作確認済み (償却予定表・当期償却の仕訳計上・
青色申告決算書への集約が整合)。

| 機能 | backend | frontend | テスト | 状態 |
|------|---------|----------|--------|------|
| 固定資産・減価償却 (M6 F-601〜603) | `domain/fixed_assets.py` / `services/depreciation.py` / `api/fixed_assets.py` | `components/FixedAssetsView.vue` | ✓ | 実装済 (定額法・月割・少額特例・家事按分) |
| 月別売上集計 (M7 F-707) | `app/api/reports.py` | (青色申告決算書に内包) | ✓ | 実装済 |
| 青色申告決算書 (M8 F-802) | `app/api/closing.py` | `components/BlueReturnView.vue` | ✓ | 実装済 (PL/BS/減価償却/月別売上の集約) |

### Phase 3 完了 (効率化)
CSV明細取込 (M5)・自動仕訳ルール/科目推測 (M2)・ダッシュボード (M7) を実装。
CSV→仕訳候補→確定→ダッシュボード反映 をブラウザで動作確認済み。

| 機能 | backend | frontend | テスト | 状態 |
|------|---------|----------|--------|------|
| ダッシュボード (M7 F-706) | `app/api/reports.py` | `components/DashboardView.vue` | ✓ | 実装済 (売上/利益/現預金/未入金) |
| 科目推測 (M2 F-105) | `services/account_suggester.py` | (取込候補に内包) | ✓ | 実装済 (摘要キーワード辞書) |
| CSV明細取込・消込 (M5 F-503/504) | `domain/imports.py` / `services/csv_import.py` / `api/imports.py` | `components/ImportWizard.vue` | ✓ | 実装済 (アダプタ解析→候補→確定/スキップ) |

### Phase 4 完了 (法令・連携)
消費税(簡易課税)集計 (M8)・証憑保存/電帳法 (X3)・CSVエクスポート (M9)・年度繰越 (M9) を実装。
集計→確定仕訳、3キー検索、CSV出力、期首振替仕訳をブラウザで動作確認済み。

| 機能 | backend | frontend | テスト | 状態 |
|------|---------|----------|--------|------|
| 消費税(簡易課税)集計 (M8 F-804) | `app/api/tax.py` | `components/TaxView.vue` | ✓ | 実装済 (税率別集計・みなし50%・納付確定仕訳) |
| 証憑保存・電帳法検索 (X3 F-402) | `domain/voucher.py` / `api/vouchers.py` | `components/VoucherView.vue` | ✓ | 実装済 (取引日/金額/取引先の3キー検索) |
| CSVエクスポート (M9 F-902) | `app/api/export.py` | `components/DataManagementView.vue` | ✓ | 実装済 (仕訳帳/試算表/PL/BS、PDFは501) |
| 年度繰越 (M9 F-904) | `app/api/year_end.py` | `components/DataManagementView.vue` | ✓ | 実装済 (損益→元入金振替の期首仕訳) |

> backend テスト 40 件パス (ruff/mypy クリーン)、frontend type-check/lint クリーン。
> 残: M3 売上売掛・M4 経費 (専用画面)、M8 決算整理ウィザード、M9 仕訳CSVインポート/バックアップ。
> 基盤強化として `add-persistence` (DB化)・`add-auth` (認証) が次の候補。
