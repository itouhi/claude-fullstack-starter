---
feature: expenses
phase: 03-basic-design
upstream:
  - 00-overall-basic-design.md
  - docs/accounting/expenses/01-requirements.md
---

# 経費・支払管理 (M4 expenses) 基本設計書

| 項目 | 内容 |
|------|------|
| 文書名 | 経費・支払管理 基本設計書 |
| バージョン | 1.0 |
| 作成日 | 2026-06-22 |
| モジュール | M4 `expenses` |
| 上位文書 | 全体基本設計書 v1.0 / 経費・支払管理 要件定義書 v1.0 |

> 本書は全体基本設計書(共通データモデル §4・API規約 §5・並列開発 §6)を前提とする。矛盾が生じた場合は全体基本設計書を優先する。

---

## 1. 設計方針

### 1.1 基本方針

- **仕訳への正規化**: すべての経費計上・未払金消込は `JournalEntry` として仕訳ストアに書き込む(全体設計 §1.3-1)。M4 固有の経費専用テーブルは設けない。
- **未払金の表現**: 未払金は勘定科目 305(未払金)を使った仕訳で表現し、新エンティティを追加しない。残高は仕訳ストアの残高計算(§4.1)で自動導出する。
- **証憑エンティティ(Voucher)**: 電帳法対応のため、ファイル実体 + メタ情報(取引日・金額・取引先・紐づく仕訳 ID)を独立エンティティとして管理する(全体設計 §4・X3)。
- **税区分の既定提案**: 経費科目マスタの `default_tax_code` を利用して、ユーザーの入力負担を軽減する(REQ-401-04)。

### 1.2 レイヤ構成

全体設計 §1.2 のレイヤ責務に従う:

```
[API]      app/api/expenses.py          — HTTP I/F・バリデーション
[サービス]  app/services/expenses.py    — 仕訳生成ロジック・税区分提案・未払集計
[ドメイン]  app/domain/journal.py       — JournalEntry/JournalLine (共通基盤)
            app/domain/voucher.py       — Voucher エンティティ (M4 追加)
[ストア]    app/store.py                — 仕訳・証憑の in-memory 保管 (共通基盤拡張)
[Frontend] src/services/expenses.ts    — 型付き API クライアント
            src/components/Expenses*.vue — 経費入力フォーム・未払一覧
```

---

## 2. データモデル

### 2.1 既存共通モデルの利用

M4 が生成する仕訳は既存の `JournalEntry` / `JournalLine` (全体設計 §4) をそのまま使用する。追加フィールドは `JournalEntry.source` を `"expenses"` にセットすることで識別する。

```
JournalEntry (既存 — app/domain/journal.py)
  id, date, description, fiscal_year, lines[], source="expenses",
  status (ACTIVE/CORRECTED/DELETED), created_at, updated_at

JournalLine (既存)
  side (DEBIT/CREDIT), account_code, sub_account, amount (整数円),
  tax_code, tax_amount
```

### 2.2 Voucher エンティティ (BD-201)

電帳法の検索要件(X3: 取引日・金額・取引先の3キー)に対応するため、証憑メタ情報を独立エンティティとして定義する。

| BD-ID | フィールド | 型 | 必須 | 説明 | 由来 |
|-------|-----------|-----|------|------|------|
| BD-201-01 | id | int | 必須 | 証憑 ID (採番) | — |
| BD-201-02 | journal_entry_id | int | 必須 | 紐づく仕訳 ID | X3 / REQ-402-01 |
| BD-201-03 | file_path | string | 必須 | サーバ上のファイルパス | REQ-402-04 |
| BD-201-04 | original_filename | string | 必須 | アップロード元ファイル名 | — |
| BD-201-05 | mime_type | string | 必須 | `image/jpeg` / `image/png` / `application/pdf` | REQ-402-01 |
| BD-201-06 | file_size_bytes | int | 必須 | ファイルサイズ(バイト) | REQ-402-06 |
| BD-201-07 | transaction_date | date | 必須 | 証憑上の取引日 (電帳法検索キー) | N-5 / X3 |
| BD-201-08 | amount | int | 必須 | 証憑上の金額・円 (電帳法検索キー) | N-5 / X3 |
| BD-201-09 | counterparty_name | string | 任意 | 取引先名 (電帳法検索キー) | N-5 / X3 |
| BD-201-10 | is_active | bool | 必須 | 論理削除フラグ。False = 論理削除 | REQ-402-04 / N-2 |
| BD-201-11 | created_at | datetime | 必須 | 登録日時 | N-7 |

> **設計上の注意:** `counterparty_name` は検索の利便性のため証憑エンティティに直接保持する。M1 取引先マスタの ID ではなく名称(文字列)を保持することで、マスタ変更後の検索一貫性を確保する。

**Voucher の Python 型定義 (参考):**

```python
# app/domain/voucher.py (実コードは実装フェーズで作成)
class Voucher(BaseModel):
    id: int
    journal_entry_id: int
    file_path: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    transaction_date: date
    amount: int
    counterparty_name: str | None = None
    is_active: bool = True
    created_at: datetime
```

### 2.3 経費入力リクエストスキーマ (BD-202)

| BD-ID | フィールド | 型 | 必須 | 備考 |
|-------|-----------|-----|------|------|
| BD-202-01 | date | string (ISO8601) | 必須 | 取引日 |
| BD-202-02 | expense_account_code | string | 必須 | 借方: 経費科目コード (601〜690) |
| BD-202-03 | amount | int | 必須 | 金額 (正の整数、円) |
| BD-202-04 | credit_account_code | string | 必須 | 貸方: 101 / 102 / 305 のいずれか |
| BD-202-05 | tax_code | string | 必須 | 税区分コード。省略時は科目 `default_tax_code` を適用 |
| BD-202-06 | description | string | 必須 | 摘要 (最大200文字) |
| BD-202-07 | counterparty_id | string | 任意 | 取引先 ID (M1 参照) |
| BD-202-08 | invoice_number | string | 任意 | インボイス登録番号 (T+13桁) |

---

## 3. 仕訳生成ルール (BD-301)

経費入力の3パターンを仕訳として表現する。金額は円単位の整数。税区分はユーザー選択値を使用。

### 3.1 借貸パターン一覧

| パターン | シーン | 借方 | 貸方 | 由来 |
|--------|--------|------|------|------|
| A 即時現金払い | 現金で支払った | 経費科目(601〜690) / 金額 | 現金(101) / 金額 | F-401 / REQ-402-02 |
| B 即時預金払い | 銀行振込・カードで支払った | 経費科目(601〜690) / 金額 | 普通預金(102) / 金額 | F-401 |
| C 未払金計上 | 後払い。支払いは翌月以降 | 経費科目(601〜690) / 金額 | 未払金(305) / 金額 | F-403 / REQ-403-01 |
| D 未払金消込 | C で計上した未払を支払った | 未払金(305) / 金額 | 現金(101)または普通預金(102) / 金額 | F-403 / REQ-403-03 |

### 3.2 税区分の扱い

- 経費は**課税仕入**として `TP10`(課税仕入10%)を既定値とするが、科目マスタの `default_tax_code` が優先される(例: 損害保険料は `NT`(非課税)、租税公課は `EX`(対象外))。
- 仕訳明細の `tax_amount` は `amount × tax_rate / (100 + tax_rate)` で内税額を計算し保持する(整数切り捨て)。
- 簡易課税の事業者であるため、課税仕入れの税額は仕入税額控除の対象とならない(全体設計 §4.2)。`tax_code = TP10/TP08` の明細は消費税集計(M8)で集計されるが、消費税納付額の計算には**仕入控除を用いない**。この点はユーザーへの注記として UI に表示することが望ましい(TBD)。

### 3.3 未払金消込における補助科目の活用

複数の未払計上が混在する場合の消込対応として、補助科目(`JournalLine.sub_account`)に取引先 ID または仕訳 ID を記録する設計を推奨する。具体的な補助科目設計は詳細設計フェーズで確定する(TBD)。

---

## 4. API 設計 (BD-401)

全体設計 §5 の API 規約に従う(`response_model` 必須、`/api` prefix は `main.py` 一括付与、個別ルーターに付けない)。

### 4.1 エンドポイント一覧

| BD-ID | メソッド | パス | 機能 | response_model | 由来 |
|-------|---------|------|------|---------------|------|
| BD-401-01 | GET | `/api/expenses` | 経費仕訳一覧(ページング・日付フィルタ) | `list[ExpenseResponse]` | REQ-401-09 |
| BD-401-02 | POST | `/api/expenses` | 経費仕訳を生成・登録 | `ExpenseResponse` | F-401 |
| BD-401-03 | GET | `/api/expenses/{id}` | 経費仕訳詳細 | `ExpenseResponse` | REQ-401-09 |
| BD-401-04 | PUT | `/api/expenses/{id}` | 経費仕訳の論理訂正(旧版を CORRECTED に変更後、新版を生成) | `ExpenseResponse` | REQ-401-10 / F-103 |
| BD-401-05 | POST | `/api/expenses/{id}/voucher` | 証憑ファイルの添付(multipart/form-data) | `VoucherResponse` | F-402 / REQ-402-01 |
| BD-401-06 | GET | `/api/expenses/payables` | 未払金一覧(未消込の305仕訳) | `list[PayableResponse]` | F-403 / REQ-403-02 |
| BD-401-07 | POST | `/api/expenses/payables/{id}/settle` | 未払金の支払消込仕訳を登録 | `ExpenseResponse` | F-403 / REQ-403-03 |
| BD-401-08 | GET | `/api/vouchers` | 証憑検索(取引日・金額・取引先3キー) | `list[VoucherResponse]` | N-5 / X3 / REQ-402-03 |

### 4.2 主要スキーマ(概要)

```
ExpenseResponse:
  id, date, description, fiscal_year, status,
  expense_account_code, expense_account_name,
  credit_account_code, credit_account_name,
  amount, tax_code, tax_amount,
  counterparty_id, invoice_number,
  vouchers: list[VoucherResponse],
  created_at, updated_at

VoucherResponse:
  id, journal_entry_id, original_filename, mime_type,
  file_size_bytes, transaction_date, amount, counterparty_name,
  created_at

PayableResponse:
  journal_entry_id, date, description,
  counterparty_id, counterparty_name,
  amount, settled_amount, remaining_amount,
  is_settled
```

### 4.3 仕訳生成の内部フロー

`POST /api/expenses` の処理フロー:

1. リクエストバリデーション (貸方科目が 101/102/305 のいずれか、金額 > 0 を確認)
2. 経費科目の `default_tax_code` を取得し、リクエストに税区分が未指定なら補完
3. 税額 (`tax_amount`) を計算 (内税計算: `amount × rate / (100 + rate)`, 整数切り捨て)
4. `JournalLine` を借方(経費科目) / 貸方(指定科目) で生成
5. `JournalEntry` を生成・バランス検証 (共通基盤の `_check_balanced` が自動検証)
6. 仕訳ストアに保存
7. `ExpenseResponse` を返却

---

## 5. 証憑保存設計 (X3 対応) (BD-501)

### 5.1 ファイル保存方式

電帳法 N-5 の要件である「真実性・可視性の確保」と「検索要件」への対応:

| BD-ID | 設計事項 | 内容 | 由来 |
|-------|---------|------|------|
| BD-501-01 | 保存場所 | `VOUCHER_STORAGE_DIR` 環境変数で指定するディレクトリ配下 | REQ-402-04 |
| BD-501-02 | ファイル名 | `{voucher_id}_{original_filename}` で保存(衝突回避) | — |
| BD-501-03 | 対応形式 | JPEG / PNG / PDF のみ受け付け(MIME type 検証) | REQ-402-01 |
| BD-501-04 | 最大サイズ | 10MB (TBD: 要確認) | REQ-402-06 |
| BD-501-05 | 論理削除 | `Voucher.is_active = False` で管理。物理ファイルは削除しない | REQ-402-04 / N-2 |

### 5.2 電帳法の検索要件(X3)への対応方針

電帳法では「取引日・取引金額・取引先」を条件として検索できることが求められる。

| 検索キー | 対応フィールド | 対応方式 |
|---------|--------------|---------|
| 取引日 | `Voucher.transaction_date` | 範囲検索(from/to) |
| 取引金額 | `Voucher.amount` | 範囲検索(min/max) |
| 取引先 | `Voucher.counterparty_name` | 部分一致検索 |

`GET /api/vouchers` は上記3キーをクエリパラメータとして受け付け、in-memory では線形スキャン、DB 移行後はインデックス(取引日・金額・取引先)で対応する(BD-501-06: TBD)。

---

## 6. UI 設計 (BD-601)

### 6.1 画面構成

| BD-ID | 画面・コンポーネント | ファイルパス | 機能概要 | 由来 |
|-------|----------------|------------|---------|------|
| BD-601-01 | 経費入力フォーム | `src/components/ExpenseForm.vue` | 経費仕訳の新規登録・編集。証憑アップロード欄付き | F-401 / F-402 |
| BD-601-02 | 経費一覧 | `src/components/ExpenseList.vue` | 登録済み経費の一覧表示。期間・科目フィルタ付き | REQ-401-09 |
| BD-601-03 | 未払金一覧 | `src/components/PayableList.vue` | 未消込の未払金一覧。消込ボタン付き | F-403 / REQ-403-02 |
| BD-601-04 | API クライアント | `src/services/expenses.ts` | 経費・証憑・未払金 API の型付きラッパー | 全体設計 §5 |

### 6.2 経費入力フォーム (ExpenseForm.vue) の主要要素

- **取引日**: date input (既定値: 本日)
- **経費科目**: `<select>` で `code + 日本語名称` を表示 (601〜690)
- **金額**: number input (正の整数のみ)
- **支払方法**: `<select>` で「現金 / 普通預金 / 未払(後払い)」を選択 (貸方科目に変換)
- **税区分**: `<select>` で自動提案値を初期選択。手動変更可
- **取引先**: 取引先マスタの選択 UI (M1 API 参照。TBD)
- **インボイス登録番号**: text input (任意)
- **摘要**: textarea (最大200文字)
- **証憑添付**: file input (JPEG/PNG/PDF)。登録後に別リクエストで送信

### 6.3 src/services/expenses.ts の関数設計

```typescript
// 概要のみ — 実コードは実装フェーズで作成
createExpense(req: CreateExpenseRequest): Promise<ExpenseResponse>
getExpenses(params?: ExpenseListParams): Promise<ExpenseResponse[]>
getExpense(id: number): Promise<ExpenseResponse>
updateExpense(id: number, req: UpdateExpenseRequest): Promise<ExpenseResponse>
uploadVoucher(expenseId: number, file: File, meta: VoucherMeta): Promise<VoucherResponse>
getPayables(): Promise<PayableResponse[]>
settlePayable(journalEntryId: number, req: SettleRequest): Promise<ExpenseResponse>
searchVouchers(params: VoucherSearchParams): Promise<VoucherResponse[]>
```

---

## 7. 並列開発上の結合点 (BD-701)

全体設計 §6.1 に基づく M4 の結合点を整理する。

| BD-ID | 結合対象 | 依存方向 | インターフェース | 備考 |
|-------|---------|---------|--------------|------|
| BD-701-01 | M2 仕訳エンジン | M4 → M2 (書く) | `JournalEntry` / `JournalLine` ドメインモデル・`store.journal_entries` | 共通基盤が先行する (Layer 0) |
| BD-701-02 | M1 勘定科目マスタ | M4 → M1 (読む) | `store.accounts[code]` で科目名称・`default_tax_code` を参照 | 標準科目は `store.py` 初期データで提供済み |
| BD-701-03 | M1 税区分マスタ | M4 → M1 (読む) | `store.tax_categories[code]` で税率を取得 | 同上 |
| BD-701-04 | M1 取引先マスタ | M4 → M1 (参照) | 取引先 ID の存在検証。詳細は M1 API を参照 | F-203 / REQ-401-06 |
| BD-701-05 | M7 レポート | M7 → M4 (読む) | M7 は仕訳ストア(`source="expenses"`)を直接読む。M4 に依存しない | 305科目残高 = 未払金残高 |
| BD-701-06 | X2 監査ログ | M4 → X2 (書く) | 仕訳登録・訂正・証憑添付のイベントを監査ログに記録 | N-7 / REQ-N03 |
| BD-701-07 | X3 証憑保存 | M4 が実装主体 | `Voucher` エンティティ + ファイルストレージ。電帳法検索 API は M4 が提供 | N-5 / REQ-402-03 |

M4 は M1・M2(Layer 0)の成果物にのみ依存し、M3・M5・M6 との直接依存はない。M3・M5・M6 と並行開発可能。

---

## 8. 残課題・TBD

| 項目 | 内容 | 優先度 |
|------|------|--------|
| TBD-01 | 証憑ファイルの最大サイズ (現案10MB) は要確認 | 中 |
| TBD-02 | 証憑の検索インデックス設計(DB 移行後) | 高 |
| TBD-03 | 未払消込の補助科目設計(複数未払が混在する場合の識別) | 中 |
| TBD-04 | 簡易課税ユーザーへの「仕入控除不適用」の UI 上の案内方法 | 低 |
| TBD-05 | 取引先マスタ(M1 F-203)の選択 UI との統合方式(未確定) | 中 |
| TBD-06 | 証憑の電帳法における「訂正削除の記録要件」の実装詳細 | 高 |
| TBD-07 | 家事按分(M2 F-106)への導線: 経費入力画面から案内するか否か | 低 |

---

## 変更履歴

| 版 | 日付 | 担当 | 概要 |
|----|------|------|------|
| 1.0 | 2026-06-22 | Itou Hideki | 初版作成 |
