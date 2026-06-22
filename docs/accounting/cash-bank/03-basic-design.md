---
feature: cash-bank
phase: 03-basic-design
upstream:
  - ./01-requirements.md
  - ../00-overall-basic-design.md
status: draft
---

# 基本設計書 — cash-bank (資金管理)

> 仕様の前工程（02-spec.md）はスキップし、要求事項（01-requirements.md）および全体基本設計書を直接の上位文書とする。
> 各 BD-xxx の「由来」列は REQ-xxx および全体設計（§番号）を指す。

## 1. アーキテクチャ概要

本モジュールは「仕訳を読む」モジュール（出納帳ビュー）と「仕訳を作る」モジュール（簡易入力・CSV確定）の両側面を持つ。
全体設計 §1.3 の原則「すべての取引は仕訳に正規化し、帳簿は読み取り専用ビュー」に従い、
**出納帳は専用テーブルを持たず、仕訳ストアからの口座別フィルタ＋時系列集計で導出**する。

```
[Vue SPA]
  CashBookView.vue     — 口座選択・出納帳テーブル・CSVエクスポート
  CashEntryForm.vue    — 簡易入力フォーム (入金/出金/相手科目/金額/摘要)
  ImportWizard.vue     — CSV取込ウィザード (アップロード→候補一覧→確定)
        │
        │  src/services/cashBank.ts (型付き API クライアント)
        ▼
[FastAPI BFF]  /api/cash-book/*  /api/imports/*
  app/api/cash_book.py   — 出納帳 GET / 簡易入力 POST
  app/api/imports.py     — CSV取込 POST / 確定 POST
        │
        │  app/services/cash_bank_service.py
        ▼
[ドメイン・共通基盤]
  app/domain/journal.py   — JournalEntry / JournalLine (M2)
  app/domain/accounts.py  — Account / AccountType (M1)
  app/store.py            — AccountingStore (in-memory。将来 DB へ)
```

> 全体設計 §6.1 の結合点: M5 は `POST /api/journal-entries` 相当のサービス呼び出しで仕訳を登録し、
> `GET /api/journal-entries` 相当の読み取りで出納帳を構築する。M2 の仕訳APIが確定すれば並列開発可能。

---

## 2. コンポーネント構成

| ID | コンポーネント | 役割 | 配置 | 由来 |
|----|--------------|------|------|------|
| BD-001 | `CashBookView.vue` | 口座選択付き出納帳テーブル。入金/出金/残高の行を表示 | `frontend/src/components/cash-bank/CashBookView.vue` | REQ-001〜004, REQ-011〜013 |
| BD-002 | `CashEntryForm.vue` | 簡易入力フォーム（入金/出金切替・相手科目選択・金額・摘要・日付） | `frontend/src/components/cash-bank/CashEntryForm.vue` | REQ-021〜024 |
| BD-003 | `ImportWizard.vue` | CSV取込ウィザード（ステップ: アップロード→候補確認→確定） | `frontend/src/components/cash-bank/ImportWizard.vue` | REQ-031〜034, REQ-041〜043 |
| BD-004 | `cashBank.ts` | frontend 側 API サービス層。コンポーネントから直接 fetch しない | `frontend/src/services/cashBank.ts` | 全体§5 |
| BD-005 | `app/api/cash_book.py` | 出納帳取得 API・簡易入力 API のルーター | `backend/app/api/cash_book.py` | REQ-001, REQ-021 |
| BD-006 | `app/api/imports.py` | CSV取込・消込確定 API のルーター | `backend/app/api/imports.py` | REQ-031, REQ-041 |
| BD-007 | `app/services/cash_bank_service.py` | 出納帳導出・簡易入力→仕訳化・CSV解析・候補生成のビジネスロジック | `backend/app/services/cash_bank_service.py` | REQ-001〜043 |
| BD-008 | `app/services/csv_adapters/` | 金融機関別CSVパーサ（アダプタ方式） | `backend/app/services/csv_adapters/` | REQ-032 |

---

## 3. データ設計（概念）

### 3.1 出納帳ビュー（新テーブルなし・仕訳の読み取り導出）

出納帳は **専用テーブルを作らない**。全体設計 §4.1 の「科目残高 = Σ借方 − Σ貸方」の導出原則に従い、
`AccountingStore.journal_entries` から対象口座の明細を抽出して時系列にソートし、残高を積み上げる。

```
CashBookRow (レスポンス専用 Pydantic モデル — テーブルなし)
  date          : date       — 仕訳日付
  description   : str        — 摘要
  counter_account: str       — 相手科目名（現金/預金以外の明細の科目）
  receipt       : int | None — 入金額（資産科目で借方の場合）
  payment       : int | None — 出金額（資産科目で貸方の場合）
  balance       : int        — 残高（前行の balance + receipt - payment）
  journal_entry_id: int      — 元仕訳の参照用 ID
```

**残高の符号ルール**（全体§4.1 準拠）:
- 資産科目（現金・預金）は借方残高が正（`DEBIT_POSITIVE_TYPES`）
- 仕訳明細の `side == DEBIT` → 入金（receipt）、`side == CREDIT` → 出金（payment）

### 3.2 取込明細（ImportedTransaction）

CSV取込で生成される一時的なエンティティ。確定後は `JournalEntry` に変換されて仕訳ストアに登録される。

```
ImportBatch (取込バッチ)
  id            : int
  imported_at   : datetime
  account_code  : str        — 対象口座の科目コード
  filename      : str        — 取込CSVファイル名
  adapter_name  : str        — 使用したアダプタ（金融機関識別子）
  status        : str        — "pending" | "partial" | "completed"

ImportedTransaction (取込明細)
  id            : int
  batch_id      : int        — ImportBatch への参照
  date          : date
  description   : str        — CSV の摘要列
  payment       : int | None — 出金額
  receipt       : int | None — 入金額
  balance_ref   : int | None — CSV記載の残高（参照用）
  suggested_account_code: str | None  — 摘要から推測した相手科目
  status        : str        — "pending" | "confirmed" | "skipped"
  journal_entry_id: int | None  — 確定後に紐づく仕訳 ID
```

> 初期実装は in-memory（`AccountingStore` 拡張）。永続化は `add-persistence` 適用時に DB 化（全体§8）。

### 3.3 既存エンティティの利用

| エンティティ | 所在 | M5 での用途 |
|------------|------|------------|
| `JournalEntry` / `JournalLine` | `app/domain/journal.py` | 出納帳ビューの元データ・簡易入力/確定で生成 |
| `Account` / `AccountType` | `app/domain/accounts.py` | 口座選択の候補リスト・相手科目の候補リスト |
| `AccountingStore` | `app/store.py` | 仕訳・科目マスタの読み書き |

---

## 4. インターフェース設計（API）

全体設計 §5 の規約に従う: `/api` prefix は `main.py` 一括付与、`response_model` 必須、リソース命名は snake_case。

| ID | メソッド | パス | 概要 | 由来 |
|----|---------|------|------|------|
| BD-101 | GET | `/api/cash-book/{account_code}` | 出納帳取得（口座コード指定、年度・期間フィルタ付き） | REQ-001〜004, REQ-011〜013 |
| BD-102 | POST | `/api/cash-book/entries` | 簡易入力→2明細仕訳を生成して仕訳ストアに登録 | REQ-021〜024 |
| BD-103 | GET | `/api/cash-book/{account_code}/export` | 出納帳CSV エクスポート | REQ-103 |
| BD-104 | POST | `/api/imports/csv` | CSVアップロード→ImportBatch＋ImportedTransaction 生成→候補一覧を返却 | REQ-031〜034 |
| BD-105 | GET | `/api/imports/{batch_id}` | 取込バッチの明細一覧・ステータス確認 | REQ-034 |
| BD-106 | POST | `/api/imports/{batch_id}/transactions/{id}/confirm` | 取込明細を確定→`JournalEntry` 登録＋ステータス更新 | REQ-041, REQ-042 |
| BD-107 | POST | `/api/imports/{batch_id}/transactions/{id}/skip` | 取込明細をスキップ | REQ-043 |

### リクエスト/レスポンス例（主要エンドポイント）

**GET `/api/cash-book/{account_code}`**
```
クエリパラメータ: fiscal_year (int, 必須), date_from (date, 任意), date_to (date, 任意)
レスポンス: CashBookResponse
  account_code    : str
  account_name    : str
  opening_balance : int    — 期首残高（M1 OpeningBalance 参照、未設定時 0）
  rows            : list[CashBookRow]
  closing_balance : int    — 最終行の残高
```

**POST `/api/cash-book/entries`**
```
リクエスト: CashEntryRequest
  account_code    : str    — 現金(101) または預金科目コード
  direction       : "receipt" | "payment"   — 入金 / 出金
  counter_code    : str    — 相手科目コード
  amount          : int    — 金額（円・正の整数）
  description     : str    — 摘要
  date            : date
  tax_code        : str | None   — 省略時は相手科目の default_tax_code を使用

レスポンス: JournalEntryResponse（M2 共通スキーマ）
```

**POST `/api/imports/csv`**
```
リクエスト: multipart/form-data
  file            : UploadFile   — CSVファイル
  account_code    : str          — 対象口座
  adapter         : str          — アダプタ識別子（例: "sbi", "rakuten"）

レスポンス: ImportBatchResponse
  batch_id        : int
  total_count     : int
  transactions    : list[ImportedTransactionResponse]
```

---

## 5. 処理フロー（主要シナリオ）

### 5.1 出納帳表示（F-501/F-502）

```
1. ユーザーが CashBookView で口座（101: 現金 / 102: 普通預金）と会計年度を選択
2. cashBank.ts が GET /api/cash-book/{account_code}?fiscal_year=XXXX を呼び出す
3. cash_bank_service.py が AccountingStore.journal_entries から対象科目・年度の JournalLine を抽出
4. 日付昇順にソートし、CashBookRow を生成（入金/出金の判定・残高の積み上げ）
   - 期首残高 = M1 OpeningBalance（未設定時 0）
   - 各行: balance += receipt（borrower=DEBIT） または balance -= payment（side=CREDIT）
5. CashBookResponse として返却
6. フロントで表形式に描画。CSV エクスポートボタンを表示
```

### 5.2 簡易入力→仕訳化（F-102/N-9）

```
1. ユーザーが CashEntryForm で「出金/入金・相手科目・金額・摘要・日付」を入力
2. cashBank.ts が POST /api/cash-book/entries を呼び出す
3. cash_bank_service.py が 2明細仕訳を構築:
   [入金の場合]
     借方: account_code（現金/預金）  金額
     貸方: counter_code（相手科目）   金額  ← 税区分を相手科目の default_tax_code から補完
   [出金の場合]
     借方: counter_code（相手科目）   金額  ← 税区分を相手科目の default_tax_code から補完
     貸方: account_code（現金/預金）  金額
4. JournalEntry のバリデーション（借方=貸方）を M2 ドメインに委譲
5. AccountingStore.journal_entries に登録（source="cash-book"）
6. 登録済み JournalEntry を返却
7. フロントで出納帳ビューをリフレッシュ
```

### 5.3 CSV取込→候補生成→確定（F-503/F-504）

```
1. ユーザーが ImportWizard でCSVをアップロードし、口座・アダプタを選択
2. POST /api/imports/csv にファイルを送信
3. csv_adapters/<adapter>.py（金融機関別パーサ）がCSVを解析し ImportedTransaction リストを生成
   - 日付/摘要/出金/入金/残高列をアダプタが正規化
   - 摘要キーワードマッチングで suggested_account_code を推測（なければ None）
4. ImportBatch・ImportedTransaction を in-memory ストアに保存
5. ImportBatchResponse（候補一覧）をフロントに返却
6. ユーザーが候補一覧で各明細を確認・相手科目を修正し、「確定」または「スキップ」を選択
7. [確定] POST /api/imports/{batch_id}/transactions/{id}/confirm
   - ImportedTransaction から JournalEntry を生成（5.2 の仕訳化ロジックを再利用）
   - 同日付・同金額の仕訳が既存に存在する場合は警告レスポンス（REQ-042）
   - 正常時: transaction.status = "confirmed"、journal_entry_id をセット
8. [スキップ] POST /api/imports/{batch_id}/transactions/{id}/skip
   - transaction.status = "skipped"
```

### 5.4 CSVアダプタ方式（F-503 詳細）

金融機関ごとに CSV のカラム構成や日付フォーマットが異なる。アダプタ方式で差異を吸収する。

**基準CSVスキーマ（住信SBIネット銀行形式）**:
```
日付,摘要,出金金額(円),入金金額(円),残高(円)
2026-01-10,振込 ○○商店,5000,,895000
2026-01-15,売上入金,,100000,995000
```

| 列名 | 型 | 説明 |
|------|----|------|
| 日付 | date (YYYY-MM-DD) | 取引日 |
| 摘要 | str | 取引内容（科目推測のキー） |
| 出金金額(円) | int or empty | 出金額（空白 = 0） |
| 入金金額(円) | int or empty | 入金額（空白 = 0） |
| 残高(円) | int | 取引後残高（参照用） |

アダプタ追加手順:
1. `app/services/csv_adapters/<bank_name>.py` を作成し、共通インターフェース `CsvAdapter` を実装
2. `app/services/csv_adapters/__init__.py` に識別子を登録
3. テストデータCSVを `tests/fixtures/` に追加

---

## 6. 非機能設計方針

| ID | 由来 | 観点 | 方針 |
|----|------|------|------|
| BD-201 | REQ-101, N-1 | 性能 | 出納帳は仕訳明細を科目コード＋年度でフィルタ後に Python 側で集計（O(n) スキャン）。DB 化後は科目・日付インデックスで p95 < 2秒を確保。年間数万件程度では in-memory でも実用範囲内 |
| BD-202 | REQ-102, N-9 | 使いやすさ | 簡易入力フォームは「入金 / 出金」と金額・摘要のみ。仕訳の借方/貸方は画面に出さない。相手科目は名称で検索できるコンボボックス |
| BD-203 | REQ-103, N-8 | 標準形式 | CSVエクスポートは `date,description,counter_account,receipt,payment,balance` のUTF-8（BOM付き、Excelで開けること）で提供 |
| BD-204 | REQ-104, N-2 | データ整合性 | 全仕訳生成時に `JournalEntry` の `_check_balanced` バリデーションを通過させる。バリデーション失敗は HTTP 422 で返却 |
| BD-205 | 全体§9 | CSV差異対応 | アダプタ方式（BD-008）でフォーマット差異を吸収。新金融機関の追加は `CsvAdapter` 実装のみ（ルーター変更不要） |

---

## 7. 並列開発上の結合点

全体設計 §6.1 の原則に従い、M5 と他モジュールの依存を以下に限定する。

| 結合点 | 依存先 | 内容 | 未完時の代替 |
|--------|--------|------|------------|
| 仕訳登録 | M2 `journal` | `AccountingStore.journal_entries` への書き込みと `JournalEntry` スキーマ | in-memory ストアを直接操作（共通スキーマは既存 `journal.py` を利用） |
| 仕訳読み取り | M2 `journal` | `AccountingStore.journal_entries` から科目・年度フィルタで読み取り | 同上 |
| 勘定科目一覧 | M1 `core-masters` | `AccountingStore.accounts` の参照（口座選択・相手科目候補） | `store.py` の `STANDARD_ACCOUNTS` から直接参照（現状で利用可能） |
| 期首残高 | M1 `core-masters` | `OpeningBalance` エンティティの参照 | M1 未実装時は 0 円として動作（REQ-003 の条件を満たす） |
| 科目推測 | M2/F-105 | 摘要キーワードからの科目自動推測 | 初期実装は簡易キーワードマッチング（TBD）。精度向上は後工程 |

---

## 8. UI 構成（概要）

```
/cash-bank                   ← 出納帳トップ（口座選択）
  /cash-bank/book            ← 出納帳ビュー（CashBookView.vue）
    口座セレクタ（101 現金 / 102 普通預金）
    年度・期間フィルタ
    出納帳テーブル: 日付 | 摘要 | 相手科目 | 入金 | 出金 | 残高
    [簡易入力ボタン] → CashEntryForm モーダル
    [CSV取込ボタン] → ImportWizard
    [CSVエクスポート]

  /cash-bank/import          ← CSV取込ウィザード（ImportWizard.vue）
    Step 1: ファイル選択・口座・アダプタ指定
    Step 2: 候補一覧（摘要/推測科目/金額/確定/スキップ操作）
    Step 3: 完了サマリ（確定件数/スキップ件数）
```

frontend サービスは `src/services/cashBank.ts` に集約（コンポーネントから直接 fetch しない）。

---

## 9. 未決事項 (TBD)

- [ ] 対応アダプタの初期セット（SBI のみか、楽天・三菱UFJ等も含めるか）
- [ ] 科目自動推測（F-105）の実装方式（キーワード辞書 / ML）と担当モジュール
- [ ] `ImportBatch`・`ImportedTransaction` の永続化モデル（`add-persistence` 適用時）
- [ ] 重複チェックの判定条件（日付＋金額だけで十分か、摘要も含めるか）
- [ ] 期首残高 API（M1）の確定後に `CashBookResponse.opening_balance` の実装を完成させる

---

## 変更履歴

> 作成・更新のたびに概要を1行追記する（追記のみ。過去行は消さない）。

| 版 | 日付 | 変更概要 | 担当 |
|----|------|---------|------|
| 1.0 | 2026-06-22 | 初版作成 | Itou Hideki |
