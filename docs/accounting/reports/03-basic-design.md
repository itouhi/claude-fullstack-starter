---
feature: reports
phase: 03-basic-design
upstream:
  - ./01-requirements.md
  - ../00-overall-basic-design.md
status: draft
---

# 基本設計書 — reports (帳簿・レポート)

> 仕訳ストアの読み取りビューとして各帳票を実装する方式を定める。「どう集計するか」のアーキテクチャ視点。実コードは書かない。

## 1. アーキテクチャ概要

M7 は**仕訳ストアへの読み取り専用集計レイヤー**として機能する。書き込み系モジュール (M2〜M6) と結合点が「仕訳ストアの読み取りスキーマ」のみであるため、並列開発が成立する (全体基本設計 §6.1)。

```
[ブラウザ SPA — 帳票ビュー]
  └ src/views/reports/
      ├ TrialBalanceView.vue   (実装済み)
      ├ GeneralLedgerView.vue
      ├ ProfitAndLossView.vue
      ├ BalanceSheetView.vue
      ├ MonthlySalesView.vue
      └ DashboardView.vue

  src/services/reports.ts  (API クライアント集約)
        │  /api/reports/* (Vite proxy → FastAPI)
        ▼
[FastAPI — backend/app/api/reports.py]  (実装済み: trial-balance)
  ├ GET /reports/trial-balance      (実装済み)
  ├ GET /reports/journal-book       (仕訳帳)
  ├ GET /reports/general-ledger     (総勘定元帳)
  ├ GET /reports/pl                 (損益計算書)
  ├ GET /reports/bs                 (貸借対照表)
  ├ GET /reports/monthly-sales      (月別売上集計)
  └ GET /reports/dashboard          (ダッシュボード)
        │  読み取り専用
        ▼
[仕訳ストア — app/store.py :: AccountingStore]
  store.journal_entries: dict[int, JournalEntry]
  store.accounts:        dict[str, Account]
```

## 2. コンポーネント構成

| ID | コンポーネント | 役割 | 配置 | 由来 |
|----|--------------|------|------|------|
| BD-001 | `reports.py` ルーター | 全帳票 API の集約ルーター | `backend/app/api/reports.py` | REQ-021 (実装済み) |
| BD-002 | `TrialBalanceView.vue` | 合計残高試算表の表示 | `frontend/src/views/reports/` | REQ-021 (実装済み) |
| BD-003 | `GeneralLedgerView.vue` | 総勘定元帳の表示 (科目選択 + 明細一覧) | `frontend/src/views/reports/` | REQ-011〜015 |
| BD-004 | `ProfitAndLossView.vue` | 損益計算書の表示 (収益・費用・当期純利益) | `frontend/src/views/reports/` | REQ-031〜035 |
| BD-005 | `BalanceSheetView.vue` | 貸借対照表の表示 (資産・負債・純資産) | `frontend/src/views/reports/` | REQ-041〜045 |
| BD-006 | `MonthlySalesView.vue` | 月別売上集計の表示 (棒グラフ/テーブル) | `frontend/src/views/reports/` | REQ-061〜063 |
| BD-007 | `DashboardView.vue` | 数値カード4枚のダッシュボード | `frontend/src/views/reports/` | REQ-051〜053 |
| BD-008 | `reports.ts` サービス | API 呼び出しを集約する型付きクライアント | `frontend/src/services/reports.ts` | REQ-105 |
| BD-009 | `JournalListView.vue` (既存) | 仕訳帳一覧 (既存コンポーネントを位置づけ) | `frontend/src/views/` | REQ-001〜003 |

## 3. データ設計 (概念)

本モジュールは新規エンティティを持たない。すべて仕訳ストアの既存エンティティを集計して返す読み取りビューである。

| 集計対象エンティティ | 参照属性 | 役割 |
|--------------------|---------|------|
| `JournalEntry` | `id, date, fiscal_year, status, lines` | 全帳票の集計源 |
| `JournalLine` | `side, account_code, sub_account, amount, tax_code, tax_amount` | 借貸明細の積み上げ |
| `Account` | `code, name, type, order` | 科目名・区分・表示順の解決 |
| `AccountType` | ASSET/LIABILITY/EQUITY/REVENUE/EXPENSE | 残高符号の判定 |
| `DEBIT_POSITIVE_TYPES` | {ASSET, EXPENSE} | 借方正の科目区分セット (全体基本設計 §4.1) |

### 3.1 勘定残高の導出方式 (全体基本設計 §4.1 準拠)

```
科目残高 = Σ(借方明細金額) − Σ(貸方明細金額)   ← 会計上の「差引残高」

表示残高:
  AccountType in DEBIT_POSITIVE_TYPES (ASSET, EXPENSE)  → balance = debit_total − credit_total
  それ以外 (LIABILITY, EQUITY, REVENUE)                  → balance = credit_total − debit_total
```

この符号規則は実装済み試算表 (`reports.py` の `trial_balance()`) と同一。PL/BS/元帳も同じ方式で導出する。

### 3.2 集計フィルタ方針

全帳票共通:
- `status == DELETED` の仕訳は除外する (`EntryStatus.DELETED`)
- `fiscal_year` クエリパラメータが指定された場合は `entry.fiscal_year == fiscal_year` で絞り込む
- 試算表は実装済みであり、この 2 条件が適用されていることを確認済み

## 4. インターフェース設計

### 4.1 API エンドポイント一覧

全エンドポイントは `fiscal_year: int | None = None` クエリパラメータを持つ (全体基本設計 §5)。

| ID | メソッド + パス | レスポンス型 | 由来 |
|----|----------------|-------------|------|
| BD-101 | `GET /api/reports/trial-balance` | `TrialBalance` (実装済み) | REQ-021 |
| BD-102 | `GET /api/reports/journal-book` | `JournalBook` | REQ-001〜003 |
| BD-103 | `GET /api/reports/general-ledger?account_code=<str>` | `GeneralLedger` | REQ-011〜015 |
| BD-104 | `GET /api/reports/pl` | `ProfitAndLoss` | REQ-031〜035 |
| BD-105 | `GET /api/reports/bs` | `BalanceSheet` | REQ-041〜045 |
| BD-106 | `GET /api/reports/monthly-sales` | `MonthlySales` | REQ-061〜063 |
| BD-107 | `GET /api/reports/dashboard` | `Dashboard` | REQ-051〜053 |

### 4.2 レスポンス型定義 (概念)

**BD-102 JournalBook** (仕訳帳):
```
JournalBook
  fiscal_year: int | None
  entries: list[JournalBookRow]
    JournalBookRow
      entry_id: int
      date: date
      description: str
      debit_lines: list[{account_code, account_name, amount}]
      credit_lines: list[{account_code, account_name, amount}]
```

**BD-103 GeneralLedger** (総勘定元帳):
```
GeneralLedger
  account_code: str
  account_name: str
  fiscal_year: int | None
  opening_balance: int          # 期首繰越残高 (前期末の残高。期首残高マスタ未実装の間は 0)
  rows: list[GeneralLedgerRow]
    GeneralLedgerRow
      date: date
      entry_id: int
      description: str
      counter_account: str      # 相手科目名 (複合仕訳は「諸口」)
      debit_amount: int
      credit_amount: int
      running_balance: int      # 期首繰越残高 + 当行までの借貸差額累計
  closing_balance: int          # 期末残高
```

**BD-104 ProfitAndLoss** (損益計算書):
```
ProfitAndLoss
  fiscal_year: int | None
  revenues: list[PLRow]         # AccountType.REVENUE の科目
    PLRow: {account_code, account_name, amount}
  expenses: list[PLRow]         # AccountType.EXPENSE の科目
  revenue_total: int
  expense_total: int
  net_income: int               # revenue_total − expense_total (当期純利益)
```

**BD-105 BalanceSheet** (貸借対照表):
```
BalanceSheet
  fiscal_year: int | None
  assets: list[BSRow]           # AccountType.ASSET の科目
    BSRow: {account_code, account_name, balance}
  liabilities: list[BSRow]      # AccountType.LIABILITY の科目
  equities: list[BSRow]         # AccountType.EQUITY の科目 (元入金・事業主貸・事業主借)
  net_income: int               # PL と同値。純資産の部の「当期純利益」欄
  asset_total: int
  liability_total: int
  equity_total: int             # equities の balance 合計 + net_income
  # 検証: asset_total == liability_total + equity_total
```

**BD-106 MonthlySales** (月別売上集計):
```
MonthlySales
  fiscal_year: int
  months: list[MonthlySalesRow]  # 1月〜12月の 12 要素
    MonthlySalesRow
      month: int               # 1〜12
      amount: int              # 売上高科目 (code=500 など REVENUE) の当月残高
```

**BD-107 Dashboard** (ダッシュボード):
```
Dashboard
  fiscal_year: int | None
  revenue_total: int           # 当期売上高 (AccountType.REVENUE のうち売上高科目)
  net_income: int              # 当期純利益 (PL と同値)
  cash_balance: int            # 現預金残高 (現金101 + 普通預金102 の合計)
  receivables_balance: int     # 売掛金残高 (135 の借方超過額)
```

### 4.3 frontend サービス層 (BD-008)

`src/services/reports.ts` に全帳票の fetch 関数を集約する。コンポーネントからの直接 `fetch` は禁止 (CLAUDE.md 規約)。

```typescript
// 関数シグネチャのイメージ (実装はしない — 実装スキルの担当)
fetchTrialBalance(fiscalYear?: number): Promise<TrialBalance>
fetchGeneralLedger(accountCode: string, fiscalYear?: number): Promise<GeneralLedger>
fetchPL(fiscalYear?: number): Promise<ProfitAndLoss>
fetchBS(fiscalYear?: number): Promise<BalanceSheet>
fetchMonthlySales(fiscalYear: number): Promise<MonthlySales>
fetchDashboard(fiscalYear?: number): Promise<Dashboard>
```

## 5. 処理フロー (主要シナリオ)

### 5.1 損益計算書 (PL) の集計フロー

1. クエリパラメータ `fiscal_year` を受け取る
2. `store.journal_entries` を走査し、`status != DELETED` かつ年度条件を満たす仕訳を選択
3. 各仕訳の明細を科目コード別に借方・貸方合計を集計 (試算表と同一ロジック)
4. `store.accounts` から科目の `type` を引き、`REVENUE` → `revenues` リスト、`EXPENSE` → `expenses` リストに分類
5. 各科目の表示残高を導出 (REVENUE は `credit_total − debit_total`、EXPENSE は `debit_total − credit_total`)
6. `revenue_total − expense_total` = `net_income` を算出
7. `ProfitAndLoss` レスポンスを生成して返す

### 5.2 貸借対照表 (BS) の集計フロー

1. BS は **累積残高** を対象とする。`fiscal_year` が指定された場合も、その年度以前の全仕訳を含む (=当該年度末時点の残高)
   - 実装上: `entry.fiscal_year <= fiscal_year` でフィルタ (または年度未指定で全期間)
2. 科目区分別に残高を導出 (§4.1 の符号規則に従う)
3. EQUITY 科目の残高合計と PL の `net_income` を合算して `equity_total` を算出
4. `asset_total == liability_total + equity_total` を検証 (不一致は実装バグ)
5. `BalanceSheet` レスポンスを生成して返す

### 5.3 総勘定元帳の集計フロー

1. `account_code` と `fiscal_year` を受け取る
2. `fiscal_year` 指定時: 開始前の残高を `opening_balance` として計算し、当該年度の明細のみを `rows` に返す
3. 明細を日付昇順でソートし、行ごとに `running_balance` を累積計算
4. 複合仕訳 (明細が3本以上) の相手科目表示は「諸口」とする
5. `closing_balance` = `opening_balance` + 当期の借貸差額

### 5.4 月別売上集計の集計フロー

1. `fiscal_year` を必須受け取り (デフォルト: 現在年)
2. `store.journal_entries` から当該年度かつ `REVENUE` 科目 (code=500 等) の貸方明細を月別に積み上げ
3. 1月〜12月の 12 要素を返す (仕訳がない月は 0)
4. M8 `closing-tax` モジュールが本 API を参照して青色申告決算書の月別欄を生成する

## 6. 非機能設計方針

| 由来 | 観点 | 方針 |
|------|------|------|
| REQ-101 / N-1 | 性能 | 現時点は in-memory フルスキャン。DB 移行後に科目コード・会計年度のインデックスを付与し、将来は科目別残高の事前集計テーブル (`account_balances`) を追加して集計コストを O(1) に近づける |
| REQ-102 / B-1 | データ整合性 | PL の `net_income` と BS の `equity_total` (元入金等を除く当期純利益部分) が一致することをテストで検証する |
| REQ-103 / N-8 | CSV エクスポート | 帳票 API は集計データを JSON で返す。M9 `data-io` がこの JSON を受け取り CSV に変換する。本モジュールは CSV 生成を持たない |
| REQ-104 / N-10 | マルチデバイス | `<style scoped>` + レスポンシブレイアウト (CSS Grid/Flexbox)。既存 TrialBalanceView.vue のスタイルを踏襲 |
| REQ-105 | 読み取り専用分離 | `reports.py` に POST/PUT/DELETE を置かない。並列開発において M3〜M6 が仕訳を書いても M7 に影響しない |

### 6.1 パフォーマンス詳細 (N-1 対応ロードマップ)

| 段階 | 実装 | 想定規模 |
|------|------|---------|
| Phase 1 (現状) | in-memory フルスキャン | 〜数千件 (開発・PoC) |
| Phase 2 (DB 移行後) | SQLite/PostgreSQL + 科目・年度インデックス | 〜数万件/年 |
| Phase 3 (将来) | 科目別残高事前集計テーブル (差分更新) | 数万件超でも p95 < 2秒 |

### 6.2 並列開発上の結合点

- M7 reports は `store.journal_entries` と `store.accounts` の**読み取りスキーマのみ**に依存する
- M3〜M6 が仕訳を追加・訂正しても M7 の実装に影響しない (書き込み側と独立)
- M8 closing-tax は M7 の `/api/reports/pl` と `/api/reports/monthly-sales` を参照する。M7 が先行して API を確立しておくことで M8 の並列開発が可能になる

## 7. 未決事項 (TBD)

- [ ] 期首残高 (OpeningBalance マスタ) の導入前における BS の繰越計算方針: 仕訳合計のみで算出し、M1 の期首残高対応後に繰越行を追加する
- [ ] BS の `asset_total != liability_total + equity_total` となった場合のエラー処理: HTTP 500 か不整合フラグをレスポンスに含めるか
- [ ] 月別売上集計の売上科目範囲: `account_code = "500"` (売上高) のみか、REVENUE 区分全科目か (雑収入 510 を含むか)
- [ ] ダッシュボードの「未入金」算出: 売掛金残高 (135 の借方超過) のみか、M3 の消込状態と突合するか
- [ ] general-ledger の `sub_account` 絞り込み実装: クエリパラメータ追加のタイミング (Phase 1 でスキップ可)
- [ ] PL の前年比較列 (REQ-035): 対応は Phase 3 以降で検討

## 変更履歴

| 版 | 日付 | 変更概要 | 担当 |
|----|------|---------|------|
| 1.0 | 2026-06-22 | 初版作成 | Itou Hideki |
