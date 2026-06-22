---
feature: data-io
phase: 03-basic-design
upstream:
  - ./01-requirements.md
  - ../00-overall-basic-design.md
status: draft
---

# 基本設計書 — data-io (データ入出力・連携)

> 要求事項 (REQ-xxx) を実現するシステム構造を定める。「どう作るか」のアーキテクチャ視点。

## 1. アーキテクチャ概要

本モジュールは M7 `reports`・M8 `closing-tax` の集計結果を**ファイルとして出力する**変換層と、
外部CSVデータを**仕訳として取り込む**インポート層、および全データの**バックアップ・復元**層・**年度繰越**層から構成される。

```
[Vue SPA]
  src/components/DataImport.vue        ← CSVインポート画面
  src/components/DataExport.vue        ← エクスポート画面
  src/components/YearEndWizard.vue     ← 年度繰越ウィザード
  src/components/BackupRestore.vue     ← バックアップ/復元画面
  src/services/dataIo.ts               ← API クライアント (型付き)
        │  HTTPS / JSON (multipart/form-data でファイルアップロード)
        ▼
[FastAPI BFF]
  app/api/import_.py   POST /api/import/journal-csv
  app/api/export_.py   GET  /api/export/{report}?format=csv&fiscal_year=
  app/api/backup.py    POST /api/backup  /  POST /api/restore
  app/api/year_end.py  POST /api/year-end/carry-forward?fiscal_year=
                            GET  /api/year-end/carry-forward/preview?fiscal_year=
        │  依存 (読み取り専用)
        ▼
  app/services/import_service.py     ← CSV解析・バリデーション・仕訳生成
  app/services/export_service.py     ← 帳簿データ取得 → CSV変換
  app/services/backup_service.py     ← エンティティ全体のシリアライズ/デシリアライズ
  app/services/year_end_service.py   ← 年度繰越ロジック
        │  読み取り
        ▼
  [M2 journal store]  [M1 masters]  [M7 reports API]  [M8 closing-tax API]
  (仕訳ストア)          (科目/税区分/   (試算表/PL/BS)    (青色申告決算書)
                         期首残高)
```

### 1.1 設計方針

1. **集計は再実装しない**: 帳簿・決算書の数値は M7/M8 の集計結果をそのまま利用する。data-io はそれをファイル形式（CSV・JSON）へ変換する役割に特化する。
2. **仕訳検証は委譲**: CSV インポートで生成する `JournalEntry` のバランス検証は既存の `model_validator` に委譲する。独自ロジックを持たない（REQ-003 由来）。
3. **PDF は将来対応**: 当面 CSV のみ提供。API パスを確保し、format パラメータで `pdf` を受け付けた場合は `501 Not Implemented` を返す（REQ-017）。

---

## 2. コンポーネント構成

| ID | コンポーネント | 役割 | 配置 | 由来 |
|----|--------------|------|------|------|
| BD-001 | `DataImport.vue` | CSVファイル選択・インポート実行・エラーレポート表示 | `frontend/src/components/DataImport.vue` | REQ-001〜006 |
| BD-002 | `DataExport.vue` | 帳簿種別選択・期間指定・CSVダウンロード | `frontend/src/components/DataExport.vue` | REQ-011〜018 |
| BD-003 | `BackupRestore.vue` | バックアップ実行・復元ファイルアップロード・モード選択 | `frontend/src/components/BackupRestore.vue` | REQ-021〜026 |
| BD-004 | `YearEndWizard.vue` | 年度繰越ウィザード（ドライラン→確認→本実行の3ステップ） | `frontend/src/components/YearEndWizard.vue` | REQ-031〜036 |
| BD-005 | `dataIo.ts` (service) | API クライアント。`multipart/form-data` アップロード・Blob ダウンロード | `frontend/src/services/dataIo.ts` | 全 REQ |
| BD-006 | `import_.py` (router) | `POST /api/import/journal-csv` 受付・`import_service` 呼出し | `backend/app/api/import_.py` | REQ-001〜006 |
| BD-007 | `export_.py` (router) | `GET /api/export/{report}` 受付・CSV/PDF 分岐 | `backend/app/api/export_.py` | REQ-011〜018 |
| BD-008 | `backup.py` (router) | `POST /api/backup`・`POST /api/restore` 受付 | `backend/app/api/backup.py` | REQ-021〜026 |
| BD-009 | `year_end.py` (router) | `GET /api/year-end/carry-forward/preview`・`POST /api/year-end/carry-forward` | `backend/app/api/year_end.py` | REQ-031〜036 |
| BD-010 | `import_service.py` | CSV 解析・行バリデーション・仕訳生成・エラーレポート生成 | `backend/app/services/import_service.py` | REQ-001〜006 |
| BD-011 | `export_service.py` | 帳簿データ取得 → CSV シリアライザ | `backend/app/services/export_service.py` | REQ-011〜018 |
| BD-012 | `backup_service.py` | 全エンティティのシリアライズ/デシリアライズ | `backend/app/services/backup_service.py` | REQ-021〜026 |
| BD-013 | `year_end_service.py` | 年度繰越ロジック（損益振替・事業主貸借整理・期首残高生成） | `backend/app/services/year_end_service.py` | REQ-031〜036 |

---

## 3. データ設計 (概念)

本モジュールは既存エンティティを読み取り・生成するのみで、新規エンティティは最小限とする。

| エンティティ | 主な属性 | 関連 | 永続化 | 由来 |
|------------|---------|------|--------|------|
| `ImportResult` (レスポンス専用) | total, success_count, error_count, error_rows: list[ErrorRow] | — | 非永続（レスポンスのみ） | REQ-001〜006 |
| `ErrorRow` (値オブジェクト) | row_number, content, reason | ImportResult | 非永続 | REQ-003, REQ-004 |
| `BackupManifest` (JSONトップ) | version, exported_at, accounts, tax_categories, journal_entries, fixed_assets, vouchers, opening_balances | — | ファイル出力 | REQ-021〜023 |
| `YearEndPreview` (レスポンス専用) | fiscal_year, balance_forward: list[BalanceItem], profit_transfer: ProfitTransfer | — | 非永致（ドライランレスポンス） | REQ-034 |
| `BalanceItem` (値オブジェクト) | account_code, account_name, account_type, closing_balance | YearEndPreview | 非永続 | REQ-031 |
| `ProfitTransfer` (値オブジェクト) | net_income, owner_draws_debit, owner_loans_credit, transfer_to_equity | YearEndPreview | 非永続 | REQ-032, REQ-033 |
| `CarryForwardStatus` | fiscal_year, executed_at, executed_by | — | in-memory → DB（`add-persistence` 後） | REQ-035 |
| `OpeningBalance` (既存・M1) | fiscal_year, account_code, amount | M1 stores | in-memory → DB | REQ-031 |

### 3.1 CSVインポートのスキーマ定義

仕訳インポートCSVのカラム定義（ヘッダ行必須）:

| 列名 | 型 | 必須 | 説明 | バリデーション |
|------|-----|------|------|--------------|
| `date` | YYYY-MM-DD | ○ | 取引日 | ISO 8601日付。未来日は警告のみ |
| `description` | 文字列 | ○ | 摘要 | 空文字不可。最大200文字 |
| `debit_account` | 科目コード | ○ | 借方科目コード | マスタに存在すること（REQ-004） |
| `debit_amount` | 整数 | ○ | 借方金額（円） | 1以上の正整数 |
| `credit_account` | 科目コード | ○ | 貸方科目コード | マスタに存在すること（REQ-004） |
| `credit_amount` | 整数 | ○ | 貸方金額（円） | 1以上の正整数 |
| `tax_code` | 税区分コード | 任意 | 借方科目適用の税区分 | 省略時は借方科目の `default_tax_code` を使用（REQ-005）。空の場合も同様 |

> 複合仕訳（1仕訳に複数明細）は当面スコープ外。各行を独立した2明細仕訳（借方1・貸方1）として登録する。複合仕訳対応は TBD。

### 3.2 バックアップJSONスキーマ (トップレベル)

```json
{
  "version": "1.0",
  "exported_at": "2026-06-22T15:00:00+09:00",
  "accounts": [ ... ],
  "tax_categories": [ ... ],
  "journal_entries": [ ... ],
  "opening_balances": [ ... ],
  "fixed_assets": [ ... ],
  "vouchers": [ ... ]
}
```

各配列の要素は対応するドメインモデルの JSON シリアライズ（Pydantic の `.model_dump(mode="json")`）。

---

## 4. インターフェース設計

### 4.1 API エンドポイント一覧

全体設計§5の規約に従う。`/api` prefix は `main.py` で一括付与。

| ID | メソッド | パス | 概要 | 由来 |
|----|---------|------|------|------|
| BD-101 | POST | `/api/import/journal-csv` | 仕訳CSVアップロード・インポート実行 | REQ-001〜006 |
| BD-102 | GET | `/api/export/journal-book` | 仕訳帳CSV出力 (`?fiscal_year=&from=&to=&format=csv`) | REQ-011 |
| BD-103 | GET | `/api/export/general-ledger` | 総勘定元帳CSV出力 (`?account_code=&fiscal_year=&format=csv`) | REQ-012 |
| BD-104 | GET | `/api/export/trial-balance` | 試算表CSV出力 (`?fiscal_year=&format=csv`) | REQ-013 |
| BD-105 | GET | `/api/export/pl` | 損益計算書CSV出力 (`?fiscal_year=&format=csv`) | REQ-014 |
| BD-106 | GET | `/api/export/bs` | 貸借対照表CSV出力 (`?fiscal_year=&format=csv`) | REQ-015 |
| BD-107 | GET | `/api/export/blue-return` | 青色申告決算書CSV出力 (`?fiscal_year=&format=csv`) | REQ-016 |
| BD-108 | POST | `/api/backup` | 全データのJSONバックアップ生成・ダウンロード | REQ-021〜023 |
| BD-109 | POST | `/api/restore` | バックアップJSONのアップロード・復元 (`?mode=overwrite\|merge`) | REQ-022, REQ-025 |
| BD-110 | GET | `/api/year-end/carry-forward/preview` | 年度繰越ドライラン (`?fiscal_year=YYYY`) | REQ-034 |
| BD-111 | POST | `/api/year-end/carry-forward` | 年度繰越本実行 (`?fiscal_year=YYYY`) | REQ-031〜035 |

### 4.2 主要レスポンス例

**BD-101 インポート結果 (`ImportResult`)**:
```json
{
  "total": 10,
  "success_count": 8,
  "error_count": 2,
  "error_rows": [
    {"row_number": 3, "content": "2026-01-05,...", "reason": "借方科目コード '999' が存在しません"},
    {"row_number": 7, "content": "2026-02-10,...", "reason": "借方金額(5000)と貸方金額(4000)が一致しません"}
  ]
}
```

**BD-110 年度繰越プレビュー (`YearEndPreview`)**:
```json
{
  "fiscal_year": 2025,
  "balance_forward": [
    {"account_code": "101", "account_name": "現金", "account_type": "asset", "closing_balance": 150000},
    {"account_code": "102", "account_name": "普通預金", "account_type": "asset", "closing_balance": 800000},
    {"account_code": "305", "account_name": "未払金", "account_type": "liability", "closing_balance": 30000},
    {"account_code": "400", "account_name": "元入金", "account_type": "equity", "closing_balance": 920000}
  ],
  "profit_transfer": {
    "net_income": 250000,
    "owner_draws_debit": 120000,
    "owner_loans_credit": 0,
    "transfer_to_equity": 130000
  }
}
```

### 4.3 frontend サービス (`src/services/dataIo.ts`)

```typescript
// インポート
importJournalCsv(file: File): Promise<ImportResult>

// エクスポート（Blob ダウンロード）
exportReport(report: ReportType, params: ExportParams): Promise<Blob>

// バックアップ・復元
downloadBackup(): Promise<Blob>
restoreBackup(file: File, mode: 'overwrite' | 'merge'): Promise<RestoreResult>

// 年度繰越
previewCarryForward(fiscalYear: number): Promise<YearEndPreview>
executeCarryForward(fiscalYear: number): Promise<CarryForwardResult>
```

---

## 5. 処理フロー (主要シナリオ)

### 5.1 CSVインポート処理フロー (BD-101)

```
1. [UI] ユーザーがCSVファイルを選択 → DataImport.vue
2. [UI] dataIo.ts.importJournalCsv(file) 呼出し
3. [API] POST /api/import/journal-csv (multipart/form-data)
4. [service] import_service.parse_csv(file_bytes)
   4a. ヘッダ行バリデーション（列名チェック）
   4b. 各行をループ:
       - 借方科目コードの存在確認 → 不在なら ErrorRow に追加
       - 貸方科目コードの存在確認 → 不在なら ErrorRow に追加
       - 借方金額 == 貸方金額 確認 → 不一致なら ErrorRow に追加
       - 税区分省略時: 借方科目の default_tax_code を適用
       - 全チェック通過: JournalEntry を構築（model_validator が借貸一致を再確認）
   4c. 正常行のみ store.journal_entries に追加
5. [API] ImportResult を返す (200 OK)
6. [UI] 成功件数・エラー件数を表示。エラー行があればCSVダウンロードボタンを表示
```

### 5.2 年度繰越処理フロー (BD-110→BD-111)

```
Step A — ドライラン (Preview)
1. [UI] YearEndWizard.vue: 年度選択 → 「繰越予測を確認」ボタン
2. [service] year_end_service.preview(fiscal_year)
   2a. 同一年度の CarryForwardStatus 確認 → 実行済みならエラー (REQ-035)
   2b. 資産・負債・純資産勘定の期末残高を算出
       = 期首残高 + 当年度仕訳の借方合計 - 貸方合計 (科目区分で符号解釈)
   2c. 損益計算: net_income = Σ収益勘定残高 - Σ費用勘定残高
   2d. 事業主整理: transfer_to_equity = net_income - 事業主貸残高 + 事業主借残高
   2e. YearEndPreview を返す (DB書込みなし)
3. [UI] 繰越予定残高一覧・損益振替金額を表示

Step B — 本実行 (Commit)
4. [UI] 「繰越を確定する」ボタン → 確認ダイアログ
5. [service] year_end_service.execute(fiscal_year)
   5a. 再度プレビュー計算を実行（二重実行防止フラグ確認含む）
   5b. 翌年度の OpeningBalance を生成:
       - 資産・負債・純資産 勘定: closing_balance をそのまま翌期首へ
       - 収益・費用 勘定: 期首残高 = 0（振替済みのためゼロ）
   5c. 元入金 (400) の翌期首残高を算出:
       元入金翌期首 = 今期元入金残高 + net_income - 事業主貸残高 + 事業主借残高
   5d. OpeningBalance レコードを M1 ストアに書き込む
   5e. CarryForwardStatus に実行日時・実行者を記録
   5f. 監査ログ (X2) に操作を記録
6. [API] CarryForwardResult（生成された期首残高件数）を返す
7. [UI] 完了メッセージとサマリCSVダウンロードボタンを表示
```

---

## 6. 年度繰越ロジック詳細 (F-904・REQ-031〜033)

個人事業主の年度末決算における損益振替と事業主勘定整理の確定ロジック。

### 6.1 科目区分別の繰越方針

| 科目区分 (`AccountType`) | 翌期首残高の生成方法 | 説明 |
|--------------------------|-------------------|------|
| `ASSET` (資産) | 当期末残高をそのまま期首残高に設定 | 現金・預金・売掛金・固定資産等 |
| `LIABILITY` (負債) | 当期末残高をそのまま期首残高に設定 | 未払金・預り金・未払消費税等 |
| `EQUITY` (純資産) — 元入金 (400) | 計算式で期首残高を更新（下記） | 当期利益・事業主勘定を集約 |
| `EQUITY` (純資産) — 事業主貸 (410) | 翌期首残高 = 0 | 元入金へ整理済みのためリセット |
| `EQUITY` (純資産) — 事業主借 (420) | 翌期首残高 = 0 | 元入金へ整理済みのためリセット |
| `REVENUE` (収益) | 翌期首残高 = 0 | 損益振替により元入金へ集約 |
| `EXPENSE` (費用) | 翌期首残高 = 0 | 損益振替により元入金へ集約 |

### 6.2 元入金 (400) の翌期首残高計算式

```
当期純利益    = Σ収益勘定の当期残高 − Σ費用勘定の当期残高
事業主勘定純額 = 事業主借 (420) 残高 − 事業主貸 (410) 残高
元入金翌期首  = 元入金 (400) 当期末残高 + 当期純利益 + 事業主勘定純額
```

> - 当期純利益がマイナスの場合（純損失）: 元入金からマイナスされる。
> - 事業主貸 (410) は「事業主が事業資金から私用で引き出した金額」のため、元入金から控除する（借方残高が正）。
> - 事業主借 (420) は「事業主が私財を事業へ投入した金額」のため、元入金に加算する（貸方残高が正）。

### 6.3 計算例（2025年度繰越）

| 科目 | 当期末残高 | 翌期首残高（2026年） | 備考 |
|------|-----------|-------------------|------|
| 現金 (101) | 150,000 | 150,000 | 資産 → そのまま繰越 |
| 普通預金 (102) | 800,000 | 800,000 | 資産 → そのまま繰越 |
| 未払金 (305) | 30,000 | 30,000 | 負債 → そのまま繰越 |
| 元入金 (400) 当期末 | 920,000 | 1,050,000 | 下記計算結果 |
| 事業主貸 (410) | 120,000 | 0 | 元入金へ整理・リセット |
| 事業主借 (420) | 0 | 0 | 元入金へ整理・リセット |
| 売上高 (500) | 500,000 | 0 | 損益振替・リセット |
| 費用合計 | 250,000 | 0 | 損益振替・リセット |

元入金翌期首 = 920,000 + (500,000 − 250,000) + (0 − 120,000) = **1,050,000**

---

## 7. エクスポートCSV列定義

### 7.1 仕訳帳 (BD-102)

| 列名 | 内容 |
|------|------|
| `date` | 取引日 (YYYY-MM-DD) |
| `description` | 摘要 |
| `debit_account_code` | 借方科目コード |
| `debit_account_name` | 借方科目名 |
| `debit_amount` | 借方金額 (整数) |
| `credit_account_code` | 貸方科目コード |
| `credit_account_name` | 貸方科目名 |
| `credit_amount` | 貸方金額 (整数) |
| `tax_code` | 税区分コード |
| `fiscal_year` | 会計年度 |
| `entry_id` | 仕訳ID |

### 7.2 総勘定元帳 (BD-103)

| 列名 | 内容 |
|------|------|
| `date` | 取引日 |
| `description` | 摘要 |
| `debit_amount` | 借方金額 |
| `credit_amount` | 貸方金額 |
| `balance` | 残高（期首残高からの累計） |
| `entry_id` | 仕訳ID |

> ヘッダ前に科目コード・科目名・期首残高を記載する（複数科目出力の場合は科目ごとにセクション分割）。

### 7.3 試算表 (BD-104)

| 列名 | 内容 |
|------|------|
| `account_code` | 科目コード |
| `account_name` | 科目名 |
| `account_type` | 科目区分 |
| `debit_total` | 借方合計 |
| `credit_total` | 貸方合計 |
| `balance` | 残高 |

### 7.4 PL / BS / 青色申告決算書 (BD-105〜107)

M7/M8 の集計 API が返す構造に準拠した列定義とする（詳細は M7/M8 の設計書に委譲）。
少なくとも「科目コード・科目名・金額」を含む最低限の列を出力する。

---

## 8. 非機能設計方針

| 由来 | 観点 | 方針 |
|------|------|------|
| REQ-101, N-2 | 消失防止 | バックアップ失敗時は `logging.error` で記録し、X2 監査ログにも書き込む |
| REQ-102, N-3 | 自動バックアップ | `add-persistence` 導入後に APScheduler またはOS cronで日次実行。初期は手動のみ提供 |
| REQ-103, N-8 | 標準形式 | CSV は UTF-8 BOM 付き (`﻿`)。CRLF 改行で Excel 互換 |
| REQ-104, N-7 | 監査性 | `import_`・`backup`・`restore`・`year_end` の各サービスは操作完了後に X2 監査ログへ記録 |
| REQ-105, N-4 | 安全性 | バックアップJSONは認証情報・セッション情報を除外する。`AuditLog` はバックアップ対象外 |
| REQ-106, N-1 | 性能 | 5万件仕訳の JSON シリアライズを計測。目標10秒。`add-persistence` 後にストリーミング出力も検討 |
| — | エラー処理 | CSV の文字コードエラー・壊れたJSONは `422 Unprocessable Entity` で返す。詳細は `add-observability` 準拠 |

---

## 9. 並列開発上の結合点

本モジュールは以下のモジュールに依存する。各モジュールの API が確定次第、並行実装が可能。

| 依存モジュール | 利用する契約 | 結合タイミング |
|--------------|------------|--------------|
| M1 `core-masters` | `GET /api/accounts`（科目存在確認）、`OpeningBalance` 書込みIF | M1 実装完了後 |
| M2 `journal` | `POST /api/journal-entries`（インポート時の仕訳登録） | M2 実装完了後 |
| M7 `reports` | `GET /api/reports/trial-balance`, `pl`, `bs` | M7 実装完了後 |
| M8 `closing-tax` | `GET /api/reports/blue-return` | M8 実装完了後（Phase 4） |
| X2 監査ログ | 監査ログ書込み API / デコレータ | X2 実装完了後（デコレータで後付け可） |

> M7/M8 が未実装の段階では、エクスポートAPIを `501 Not Implemented` で仮置きし、他の機能（インポート・バックアップ・年度繰越）は先行実装できる。

---

## 10. 未決事項 (TBD)

- [ ] PDFエクスポートのライブラリ選定（全体§9参照。ReportLab / WeasyPrint）と実装タイミング
- [ ] 日次自動バックアップのスケジューラ実装方式（`add-persistence` 後に確定）
- [ ] バックアップファイルの保存先（ローカルFS / S3）と保持世代数
- [ ] マージ復元（REQ-025）の詳細競合解決ルール（仕訳IDが衝突した場合の扱い）
- [ ] 複合仕訳（1仕訳に3明細以上）のCSVスキーマ拡張方式
- [ ] M7 `reports` のエクスポート用 API スキーマ確定待ち

---

## 変更履歴

> 作成・更新のたびに概要を1行追記する（追記のみ。過去行は消さない）。

| 版 | 日付 | 担当 | 概要 |
|----|------|------|------|
| 1.0 | 2026-06-22 | Itou Hideki | 初版作成 |
