---
feature: receivables
phase: 03-basic-design
upstream:
  - ./01-requirements.md
  - ../00-overall-basic-design.md
status: draft
---

# 基本設計書 — receivables (売上・売掛管理)

> 要求事項 (REQ-xxx) を実現するシステム全体の構造を決める。「どう作るか」のアーキテクチャ視点。
> 本書の決定事項は全体基本設計書 (`00-overall-basic-design.md`) の共通規約に準拠する。

## 1. アーキテクチャ概要

全体基本設計 §1.1 の SPA + BFF 型構成を踏襲する。本モジュール固有の配置は下記の通り。

```
[Vue SPA]
  ReceivableForm.vue     (売上計上フォーム)
  ReceivableList.vue     (売掛一覧・消込)
       |
  src/services/receivables.ts   (API クライアント集約)
       |  /api/* (Vite proxy)
[FastAPI BFF]
  app/api/receivables.py        (HTTPルーター: 未消込残高照会 etc.)
  app/services/receivables.py   (ドメインサービス: 仕訳生成ロジック)
       |
  POST /api/journal-entries     (M2 仕訳エンジン — 唯一の書き込み契約)
  GET  /api/journal-entries     (M2 仕訳ストア — 読み取り)
       |
[共通基盤 (M1/M2)]
  AccountingStore (in-memory → DB移行後もインターフェース同一)
```

## 2. コンポーネント構成

| ID | コンポーネント | 役割 | 配置 | 由来 |
|----|--------------|------|------|------|
| BD-001 | `ReceivableForm.vue` | 売上計上フォーム。役務提供日・取引先・税込金額・摘要を入力し売上仕訳を生成 | `frontend/src/components/ReceivableForm.vue` | REQ-001〜005 |
| BD-002 | `ReceivableList.vue` | 売掛一覧・入金消込。取引先別未消込残高を表示し、入金登録フォームを内包 | `frontend/src/components/ReceivableList.vue` | REQ-011〜015 |
| BD-003 | `src/services/receivables.ts` | フロントエンドの API クライアント。コンポーネントから直接 fetch しない | `frontend/src/services/receivables.ts` | REQ-001〜015 |
| BD-004 | `app/api/receivables.py` | FastAPI ルーター。`/receivables/*` エンドポイントを定義。`response_model` 必須 | `backend/app/api/receivables.py` | REQ-012〜013 |
| BD-005 | `app/services/receivables.py` | ドメインサービス。売上仕訳・入金仕訳の生成ロジック、未消込残高集計 | `backend/app/services/receivables.py` | REQ-001〜015 |

## 3. データモデル設計

### 3.1 設計方針 — 新エンティティを増やさず仕訳で表現する

| ID | 方針 | 由来 |
|----|------|------|
| BD-010 | **売掛金の管理は勘定科目(135)の仕訳で完結させる**。専用の「売掛金テーブル」等の新エンティティは導入しない | REQ-001〜015 / 全体基本設計 §1.3 |
| BD-011 | 売掛金の**取引先別管理は補助科目 (`sub_account`)** で実現する。売掛金明細の `sub_account` に取引先名を設定することで、取引先別の絞り込み・集計が可能になる | REQ-003 |
| BD-012 | **未消込残高 = 取引先別の売掛金残高 = Σ借方金額(135/取引先) − Σ貸方金額(135/取引先)**。全体基本設計 §4.1 の残高導出ルール(借方が正)を売掛金科目に適用したもの | REQ-012 |

### 3.2 仕訳パターン (M2 `JournalEntry`/`JournalLine` モデルを使用)

#### 売上計上仕訳 (F-301)

| 借貸 | 勘定科目 | 科目コード | 補助科目 | 金額 | 税区分 | 税額 |
|------|---------|-----------|---------|------|--------|------|
| 借方 (DEBIT) | 売掛金 | 135 | 取引先名 | 税込金額(整数円) | — (売掛金は対象外) | 0 |
| 貸方 (CREDIT) | 売上高 | 500 | — | 税込金額(整数円) | T10 (課税売上10%) | 内税消費税額 |

- 税額計算: `tax_amount = floor(税込金額 / 1.1 * 0.1)` (円未満切り捨て)
- `source = "receivables-sale"` を仕訳の `source` フィールドに設定し、由来を識別可能にする
- 不変条件: 借方合計 == 貸方合計 (M2 `JournalEntry._check_balanced` で自動検証)

#### 入金仕訳 (F-302)

| 借貸 | 勘定科目 | 科目コード | 補助科目 | 金額 | 税区分 | 税額 |
|------|---------|-----------|---------|------|--------|------|
| 借方 (DEBIT) | 普通預金または現金 | 102 または 101 | — | 入金額(整数円) | — (対象外) | 0 |
| 貸方 (CREDIT) | 売掛金 | 135 | 取引先名 | 入金額(整数円) | — (売掛金は対象外) | 0 |

- 入金口座は UI で「普通預金 / 現金」を選択。デフォルトは普通預金(102)
- `source = "receivables-payment"` を設定
- 入金で売掛金の貸方を立てることで、取引先別残高(借方−貸方)が減少し消込が完成する

### 3.3 既存モデルとの整合

| 要素 | 使用するモデル | コード/値 | 確認済み |
|------|--------------|---------|---------|
| 売掛金科目 | `Account` (store.py) | code=`"135"`, type=ASSET | 標準科目マスタに存在 |
| 売上高科目 | `Account` (store.py) | code=`"500"`, type=REVENUE, default_tax_code=`"T10"` | 標準科目マスタに存在 |
| 普通預金科目 | `Account` (store.py) | code=`"102"`, type=ASSET | 標準科目マスタに存在 |
| 現金科目 | `Account` (store.py) | code=`"101"`, type=ASSET | 標準科目マスタに存在 |
| 売上税区分 | `TaxCategory` (store.py) | code=`"T10"`, rate_percent=10, business_type=5 | 標準税区分マスタに存在 |
| 金額型 | `JournalLine.amount` | 正の整数 (円単位) | ドメインモデルに準拠 |

## 4. API 設計

全体基本設計 §5 の URL 規約に準拠。個別ルーターに `/api` prefix を付けず `main.py` で一括付与する。`response_model` を必ず指定する。

### 4.1 エンドポイント一覧

| ID | メソッド | パス | 概要 | `response_model` | 由来 |
|----|---------|------|------|-----------------|------|
| BD-101 | GET | `/api/receivables/outstanding` | 取引先別 未消込売掛残高一覧 | `list[OutstandingItem]` | REQ-012〜013 |
| BD-102 | POST | `/api/receivables/sales` | 売上計上: 仕訳を生成して登録 | `JournalEntryResponse` | REQ-001〜005 |
| BD-103 | POST | `/api/receivables/payments` | 入金消込: 入金仕訳を生成して登録 | `JournalEntryResponse` | REQ-011〜015 |

> 仕訳の訂正・削除は共通エンドポイント `PUT/DELETE /api/journal-entries/{id}` (M2) を使用する。本モジュールは専用の訂正エンドポイントを持たない。

### 4.2 結合点: 仕訳ストア契約

- BD-102, BD-103 のサービス層は内部的に `POST /api/journal-entries` 相当のロジック (全体基本設計 §6.1) を呼び出して仕訳を生成・保存する
- BD-101 は `GET /api/journal-entries` に相当する仕訳ストアの読み取りを行い、科目=135 の明細を取引先(補助科目)別に集計して返す
- **他モジュール(M4〜M9)のコードを直接参照しない**。依存するのは仕訳ストアのモデル (`JournalEntry`, `JournalLine`) と科目・税区分マスタのみ

### 4.3 主要スキーマ (概念)

```
# リクエスト: 売上計上
SaleRequest:
  date: str (YYYY-MM-DD)        # 役務提供日
  counterparty: str             # 取引先名 (補助科目に設定)
  amount_including_tax: int     # 税込金額 (円、正の整数)
  description: str              # 摘要

# リクエスト: 入金消込
PaymentRequest:
  date: str (YYYY-MM-DD)        # 入金日
  counterparty: str             # 取引先名 (売掛金の補助科目と一致させること)
  amount: int                   # 入金額 (円、正の整数)
  bank_account_code: str        # 入金口座科目コード ("102" or "101")
  description: str              # 摘要

# レスポンス: 未消込残高明細
OutstandingItem:
  counterparty: str             # 取引先名
  total_billed: int             # 売掛金発生額合計 (借方合計)
  total_received: int           # 入金消込額合計 (貸方合計)
  outstanding_balance: int      # 未消込残高 = total_billed - total_received
```

## 5. 処理フロー (主要シナリオ)

### 5.1 売上計上フロー (REQ-001〜005)

```
1. ユーザーが ReceivableForm.vue に「役務提供日・取引先・税込金額・摘要」を入力
2. 送信ボタン押下 → receivables.ts の postSale() が POST /api/receivables/sales を呼び出す
3. app/api/receivables.py が SaleRequest を受信
4. app/services/receivables.py が仕訳を組み立てる:
   a. tax_amount = floor(amount_including_tax / 1.1 * 0.1)
   b. 借方明細: account_code="135", sub_account=counterparty, amount=amount_including_tax
   c. 貸方明細: account_code="500", amount=amount_including_tax, tax_code="T10", tax_amount=tax_amount
   d. JournalEntry を構築し、バランス検証 (M2 _check_balanced)
5. 仕訳ストアに保存 (store.journal_entries)
6. 生成された JournalEntry を JSON で返却
7. ReceivableForm.vue が成功を表示し、フォームをリセット
```

### 5.2 入金消込フロー (REQ-011〜015)

```
1. ユーザーが ReceivableList.vue の取引先行から入金登録を開始
2. 入金日・入金額・入金口座・摘要を入力して送信
3. receivables.ts の postPayment() が POST /api/receivables/payments を呼び出す
4. app/services/receivables.py が入金仕訳を組み立てる:
   a. 借方明細: account_code=bank_account_code (102 or 101), amount=amount
   b. 貸方明細: account_code="135", sub_account=counterparty, amount=amount
   c. JournalEntry を構築し、バランス検証
5. 仕訳ストアに保存
6. ReceivableList.vue が未消込残高を再取得して表示を更新
```

### 5.3 未消込残高照会フロー (REQ-012〜013)

```
1. ReceivableList.vue のマウント時に receivables.ts の fetchOutstanding() が
   GET /api/receivables/outstanding を呼び出す
2. app/api/receivables.py が仕訳ストアから科目コード="135" の全明細を取得
3. 取引先(sub_account)別に借方合計・貸方合計を集計
4. outstanding_balance = 借方合計 - 貸方合計 を算出
5. balance > 0 の取引先のみ(または全取引先)を OutstandingItem[] として返却
6. フロントが件数・合計金額のサマリと取引先別一覧を表示
```

## 6. UI 設計

### 6.1 売上計上フォーム (BD-001: ReceivableForm.vue)

```
┌─────────────────────────────────────────────┐
│  売上を登録する                               │
│                                             │
│  役務提供日  [ 2026-06-22       ▼]           │
│  取引先      [ 株式会社△△         ]          │
│  税込金額    [ 110,000           ] 円        │
│  (内消費税    10,000 円  ← 自動計算)         │
│  摘要        [ Webサイト制作6月分   ]         │
│                                             │
│            [キャンセル]  [売上を計上する →]   │
└─────────────────────────────────────────────┘
```

- 税込金額入力時に `tax_amount = floor(amount / 1.1 * 0.1)` をリアルタイム表示(参考表示)
- フォーム送信後は `<script setup>` の `ref` で状態管理。成功メッセージを 3 秒表示してリセット

### 6.2 売掛一覧・消込画面 (BD-002: ReceivableList.vue)

```
┌─────────────────────────────────────────────────────────┐
│  売掛金管理                                              │
│                                                         │
│  未入金: 3件  合計 ¥385,000                              │
│                                                         │
│  取引先          発生額       入金済    未収残    操作    │
│  ─────────────────────────────────────────────────────  │
│  株式会社△△   330,000    220,000   110,000  [入金登録]  │
│  個人 山田太郎  165,000          0   165,000  [入金登録]  │
│  有限会社□□   110,000    110,000         0  (消込済)    │
│                                                         │
│  [+ 売上を登録する]                                      │
└─────────────────────────────────────────────────────────┘
```

入金登録モーダル (ReceivableList.vue 内インライン):
```
┌────────────────────────────────────────┐
│  入金を記録する — 株式会社△△            │
│                                        │
│  入金日    [ 2026-06-25    ▼]          │
│  入金額    [ 110,000       ] 円        │
│  入金口座  [ 普通預金 ▼]               │
│  摘要      [ 6月分入金      ]          │
│                                        │
│       [キャンセル]  [入金を記録する →]  │
└────────────────────────────────────────┘
```

- `<script setup lang="ts">` + Composition API で統一
- Props/Emits は TypeScript の型で定義 (runtime declaration は使わない)
- スタイルは `<style scoped>`

## 7. 非機能設計方針

| ID | 由来 (REQ) | 観点 | 方針 |
|----|-----------|------|------|
| BD-201 | REQ-101 | 性能 | 売掛残高照会は `account_code="135"` の明細を全件取得して Python 側で集計する。年間数万件規模では問題ないが、将来は DB インデックス(科目コード・補助科目)で対応 (全体設計 N-1) |
| BD-202 | REQ-102 | データ保全 | 訂正・削除は M2 の論理管理機構(status=corrected/deleted)を使用。receivables サービスが直接 `journal_entries` を物理削除しない |
| BD-203 | REQ-103 | 監査ログ | X2 の共通監査ログ機構を使用。売上計上・入金登録の各 mutation で自動記録される。receivables サービスは監査ログロジックを個別に持たない |
| BD-204 | REQ-104 | ユーザビリティ | UI で「借方/貸方」「勘定科目コード」等の専門用語を使わない。「売上を登録する」「入金を記録する」「未収残高」等の業務用語を使用する |

## 8. 並列開発上の結合点

| 結合先 | 依存する契約 | 依存しないもの |
|--------|------------|--------------|
| M2 `journal` | `JournalEntry`, `JournalLine` モデル / `POST /api/journal-entries` 相当のストア書き込み / `GET /api/journal-entries` 相当の読み取り | M2 の内部実装詳細 |
| M1 `core-masters` | 勘定科目コード (135/500/102/101)・税区分コード (T10) の存在 | M1 の API エンドポイント実装 |
| M4〜M9 各モジュール | **一切依存しない** | — |
| X2 監査ログ | 共通デコレータ/依存の存在 (未導入時は TBD) | X2 の実装詳細 |

> **結合の方向**: 本モジュール(M3) → 仕訳ストア(M2) → M4〜M9 が仕訳ストアを読む、という単方向依存。M3 は M4〜M9 を参照しない。全体設計 §6.1 の並列開発根拠に準拠する。

## 9. 未決事項 (TBD)

- [ ] 取引先マスタ (M1-F205) 導入後の移行: 補助科目を自由入力文字列から取引先IDへ切り替える際のデータ移行方針
- [ ] 過入金時の警告実装レベル: ダイアログ確認のみか、強制ブロックにするか (REQ-014 は「警告して計上可」と定義済み)
- [ ] 未消込残高 API: balance = 0 の取引先(消込済)を含めるか、未収分のみ返すか。UI のユースケースに依存
- [ ] X2 監査ログが未導入の場合の暫定措置 (REQ-103)

## 変更履歴

| 版 | 日付 | 変更概要 | 担当 |
|----|------|---------|------|
| 1.0 | 2026-06-22 | 初版作成 | Itou Hideki |
