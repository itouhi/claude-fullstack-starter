---
feature: closing-tax
phase: 03-basic-design
upstream:
  - ./01-requirements.md
  - ../00-overall-basic-design.md
status: draft
---

# 基本設計書 — closing-tax (決算・確定申告・消費税)

> 仕様 (REQ-xxx) を実現するシステム構造を決める。全体基本設計 (§1〜§6) の決定事項を前提とし、M8 固有の設計を定める。

## 1. アーキテクチャ概要

M8 は Layer 3 (集約層) に位置する。M6(固定資産)・M7(帳簿集計)の出力を読み取り専用で参照し、決算整理仕訳の生成(書き込み)と申告データの集約(読み取り)を担う。

```
[ブラウザ SPA]
  ClosingWizard.vue          ← 決算整理ウィザード (F-801)
  TaxSummary.vue             ← 消費税集計表 (F-804)
  BlueReturnPreview.vue      ← 青色申告決算書プレビュー (F-802)
  src/services/closingTax.ts ← API クライアント(型付き)
       │
       │ HTTPS / JSON
       ▼
[BFF / API]  FastAPI
  app/api/closing.py         ← POST /api/closing/adjustments (決算整理仕訳)
  app/api/tax.py             ← GET  /api/tax/consumption (消費税集計)
  app/api/closing.py         ← GET  /api/closing/blue-return (青色申告決算書データ)
       │
       ▼
[サービス層]
  app/services/closing_tax.py
    ClosingTaxService         ← 消費税集計・決算整理仕訳生成
    BlueReturnService         ← 青色申告決算書データ集約
       │                   ↑
       │           (読み取り参照)
       ├─ app/services/reports.py (M7: PL/BS/月別集計)
       ├─ app/services/fixed_assets.py (M6: 減価償却明細)
       └─ app/store.py (仕訳ストア・科目/税区分マスタ)
```

## 2. コンポーネント構成

| ID | コンポーネント | 役割 | 配置 | 由来 |
|----|--------------|------|------|------|
| BD-001 | `ClosingWizard.vue` | 決算整理ウィザード。減価償却・家事按分・前払/未払の整理仕訳を順序立てて生成・確認 | `frontend/src/components/ClosingWizard.vue` | REQ-001〜005 |
| BD-002 | `TaxSummary.vue` | 消費税集計表。税率別課税売上・消費税額・控除税額・納付税額を表示。納付仕訳確定ボタン | `frontend/src/components/TaxSummary.vue` | REQ-030〜034 |
| BD-003 | `BlueReturnPreview.vue` | 青色申告決算書プレビュー。PL/BS/減価償却/月別売上の様式マッピング結果を表示。CSV/PDFエクスポート | `frontend/src/components/BlueReturnPreview.vue` | REQ-010〜014, REQ-020〜022 |
| BD-004 | `src/services/closingTax.ts` | closing-tax モジュールの全 API 呼び出しを集約した型付きクライアント | `frontend/src/services/closingTax.ts` | 全 REQ |
| BD-011 | `app/api/closing.py` | `POST /api/closing/adjustments` (決算整理仕訳登録)、`GET /api/closing/blue-return` (青色申告決算書データ) | `backend/app/api/closing.py` | REQ-001〜005, REQ-010〜014 |
| BD-012 | `app/api/tax.py` | `GET /api/tax/consumption` (消費税簡易課税集計) | `backend/app/api/tax.py` | REQ-030〜034 |
| BD-013 | `app/services/closing_tax.py` | `ClosingTaxService`: 消費税集計ロジック・決算整理仕訳生成。`BlueReturnService`: 青色申告決算書データ集約 | `backend/app/services/closing_tax.py` | 全 REQ |

## 3. データ設計 (概念)

M8 は独自の永続化エンティティを持たない。既存のエンティティ(JournalEntry・FixedAsset)を参照・生成する。

| エンティティ | 主な属性 | M8 での利用 | 永続化 | 由来 |
|------------|---------|-----------|--------|------|
| `JournalEntry` (M2) | id, date, fiscal_year, lines, source, status | 消費税集計の入力元(source問わず)・決算整理仕訳の出力先(source="closing-adjustment") | in-memory → DB(add-persistence) | REQ-001〜005, REQ-030〜034 |
| `JournalLine` (M2) | side, account_code, amount, tax_code, tax_amount | 課税売上明細の積み上げ(tax_code=T10/T08) | 同上 | REQ-030〜034 |
| `TaxCategory` (M1) | code, kind, rate_percent, business_type | 事業区分(business_type=5)・税率の参照 | in-memory → DB | REQ-030〜032 |
| `FixedAsset` (M6) | 取得価額, 耐用年数, 本年分償却額, 期末帳簿価額 | 減価償却決算整理仕訳の元データ・青色申告決算書減価償却明細 | in-memory → DB | REQ-001, REQ-012 |
| `ConsumptionTaxSummary` (M8 出力DTO) | fiscal_year, tax_rate, taxable_sales, tax_amount, deemed_purchase_rate, deductible_amount, payable_amount, lines_ref | 消費税集計APIのレスポンス。永続化しない(仕訳から毎回集計) | なし(計算結果DTO) | REQ-030〜034 |
| `BlueReturnData` (M8 出力DTO) | fiscal_year, pl_map, bs_map, depreciation_list, monthly_sales | 青色申告決算書APIのレスポンス。永続化しない | なし(集約結果DTO) | REQ-010〜014 |

## 4. API 設計

全体基本設計 §5 の規約に従う(`/api` prefix は `main.py` 一括付与、`response_model` 必須)。

| ID | メソッド | パス | 概要 | 由来 |
|----|---------|------|------|------|
| BD-101 | `POST` | `/api/closing/adjustments` | 決算整理仕訳を登録する。種別(depreciation/household/prepaid/accrued)と必要パラメータを受け取り、JournalEntry (source="closing-adjustment") を生成して返す | REQ-001〜005 |
| BD-102 | `GET` | `/api/closing/blue-return?fiscal_year=` | 指定会計年度の青色申告決算書データ(PL/BS/減価償却/月別売上)を集約して返す | REQ-010〜014 |
| BD-103 | `GET` | `/api/tax/consumption?fiscal_year=` | 指定会計年度の消費税簡易課税集計(課税売上・消費税額・控除税額・納付税額)を返す | REQ-030〜034 |
| BD-104 | `POST` | `/api/tax/consumption/finalize` | 消費税納付確定仕訳(借方:租税公課601 / 貸方:未払消費税330)を登録する | REQ-033 |
| BD-105 | `GET` | `/api/closing/blue-return/export?fiscal_year=&format=csv\|pdf` | 青色申告決算書データを CSV または PDF でエクスポートする | REQ-020〜022 |

### 4.1 リクエスト/レスポンス概要

**BD-103 `GET /api/tax/consumption` レスポンス例**:
```json
{
  "fiscal_year": 2025,
  "business_type": 5,
  "deemed_purchase_rate": 0.50,
  "tax_rates": [
    {
      "rate_percent": 10,
      "tax_code": "T10",
      "taxable_sales_base": 5000000,
      "tax_amount": 500000,
      "deductible_amount": 250000,
      "payable_amount": 250000,
      "journal_line_ids": [1, 5, 12]
    },
    {
      "rate_percent": 8,
      "tax_code": "T08",
      "taxable_sales_base": 0,
      "tax_amount": 0,
      "deductible_amount": 0,
      "payable_amount": 0,
      "journal_line_ids": []
    }
  ],
  "total_tax_amount": 500000,
  "total_deductible_amount": 250000,
  "total_payable_amount": 250000
}
```

**BD-101 `POST /api/closing/adjustments` リクエスト例(家事按分)**:
```json
{
  "fiscal_year": 2025,
  "type": "household",
  "account_code": "602",
  "household_ratio_percent": 30,
  "description": "水道光熱費 家事按分 30%"
}
```

## 5. 消費税簡易課税の計算式 (確定)

全体基本設計 §4.2 の税計算ルールを具体的な計算手順として定義する。

### 5.1 計算式

```
【ステップ1】税率別の課税標準額に対する消費税額
  消費税額(税率r%) = Σ(税区分=Tr の売上仕訳明細の tax_amount)

【ステップ2】みなし仕入率による控除税額
  控除税額(税率r%) = 消費税額(税率r%) × みなし仕入率(第五種=50%)
                    ※端数切捨て(円単位)

【ステップ3】税率別納付税額
  納付税額(税率r%) = 消費税額(税率r%) − 控除税額(税率r%)

【ステップ4】合計納付税額
  合計納付税額 = Σ 納付税額(税率r%)  ※複数税率の合算
```

**前提**:
- 課税売上の消費税額は `JournalLine.tax_amount` に明細単位で記録済み(仕訳入力時に計算・保持)。
- 積み上げ計算: 消費税額を明細 `tax_amount` から積み上げる(逆算しない)。
- 端数処理: 控除税額の計算で小数が生じた場合は**切捨て**(REQ-034)。

### 5.2 数値例

| 項目 | 税率10% | 税率8%(軽減) | 合計 |
|------|---------|------------|------|
| 課税売上(税抜) | 5,000,000円 | 0円 | 5,000,000円 |
| 消費税額(Σtax_amount) | 500,000円 | 0円 | 500,000円 |
| みなし仕入率 | 50% | 50% | — |
| 控除税額 | 250,000円 | 0円 | 250,000円 |
| **納付税額** | **250,000円** | **0円** | **250,000円** |

### 5.3 複数事業区分への拡張余地

現状は business_type = 5 (第五種、みなし仕入率50%) のみ対応。将来的に複数事業区分が混在する場合:
- `TaxCategory.business_type` の値ごとに課税売上を分類し、それぞれ対応するみなし仕入率を適用する。
- 各業種のみなし仕入率は税区分マスタに `deemed_purchase_rate` 列を追加して管理する。
- 詳細設計・実装は全体基本設計 §9 の残課題として扱う(REQ-032, 全体BD §9)。

### 5.4 消費税納付確定仕訳

消費税額確定時に以下の仕訳を登録する(BD-104)。

| 借方科目 | 借方科目コード | 貸方科目 | 貸方科目コード | 金額 | 摘要例 |
|---------|------------|---------|------------|------|--------|
| 租税公課 | 601 | 未払消費税 | 330 | 納付税額 | 消費税確定 2025年度 |

> 未払消費税 (コード330) は `backend/app/store.py` の標準勘定科目に定義済み。
> 実際の納付時には借方:未払消費税330 / 貸方:普通預金102 の仕訳を別途登録する(F-801の範囲外、通常仕訳で処理)。

## 6. 青色申告決算書の集約設計

### 6.1 データ源と様式欄のマッピング

| 青色申告決算書様式 | M8 内でのデータ源 | 依存API/機能 | 由来 |
|----------------|----------------|------------|------|
| 第1表 損益計算書(収支計算) | M7 PL集計 (`GET /api/reports/pl`) | F-704(M7) | REQ-010 |
| 第3表 貸借対照表 | M7 BS集計 (`GET /api/reports/bs`) | F-705(M7) | REQ-011 |
| 第3表 減価償却費の計算 | M6 固定資産台帳 (`GET /api/fixed-assets`) の当期償却額 | F-602(M6) | REQ-012 |
| 月別売上金額 | M7 月次推移 (`GET /api/reports/monthly`) の売上高(科目500)抽出 | F-707(M7) | REQ-013 |

### 6.2 BlueReturnService の責務

1. `GET /api/reports/pl?fiscal_year=` を呼び出し、PL各行を青色申告決算書 第1表の欄名にマッピングする。
2. `GET /api/reports/bs?fiscal_year=` を呼び出し、BS各行を第3表の欄名にマッピングする。
3. `GET /api/fixed-assets?fiscal_year=` を呼び出し、固定資産台帳の当期分減価償却計算明細を生成する。
4. `GET /api/reports/monthly?fiscal_year=` を呼び出し、科目コード500(売上高)の月別金額を12ヶ月分抽出する。
5. 上記4つを `BlueReturnData` DTOに集約して返す。

### 6.3 依存インターフェースと結合タイミング

- M6・M7 の内部サービス関数(または HTTP API)を直接呼ぶ設計とする。
- M6/M7 未完成時はスタブ(ゼロ値レスポンス)で代替し、単体テスト可能とする。
- 結合テストは M6・M7 の API が安定した段階(Layer 2 完了後)に実施する。

## 7. 申告データ出力設計 (F-803)

e-Tax への直接送信は当面スコープ外(全体BD §9 残課題)。

| 出力形式 | 実装方針 | 由来 |
|---------|---------|------|
| CSV | API レスポンス(JSON)をフロントエンドで CSV 変換して `<a download>` ダウンロード | REQ-020, N-8 |
| PDF | ブラウザの `window.print()` またはフロント側の PDF ライブラリ(未定: TBD)でプレビューから生成 | REQ-021, N-8 |
| e-Tax 参照 | CSV の科目・金額をe-Tax 入力画面への手入力補助として利用。直接送信は将来フェーズ | REQ-022 |

税理士との共有は CSV/PDF ダウンロードで実現(N-8)。

## 8. 処理フロー (主要シナリオ)

### 8.1 消費税簡易課税集計フロー

```
1. 利用者が TaxSummary.vue で会計年度を選択し「集計」をクリック
2. closingTax.ts が GET /api/tax/consumption?fiscal_year=2025 を呼び出す
3. app/api/tax.py が ClosingTaxService.calc_consumption_tax(2025) を呼ぶ
4. サービスが仕訳ストアから fiscal_year=2025 かつ status=ACTIVE の全仕訳明細を取得
5. tax_code = T10/T08 かつ貸方(CREDIT)明細の tax_amount を税率別に積み上げる
6. 税率別に控除税額(×50%、切捨て)・納付税額を計算
7. ConsumptionTaxSummary DTO を組み立て response_model で返す
8. TaxSummary.vue が集計結果と元仕訳ID一覧を表示
9. 利用者が「納付仕訳を確定」→ POST /api/tax/consumption/finalize → BD-013で仕訳生成
```

### 8.2 青色申告決算書集約フロー

```
1. 利用者が BlueReturnPreview.vue で会計年度を選択
2. closingTax.ts が GET /api/closing/blue-return?fiscal_year=2025 を呼び出す
3. BlueReturnService が以下を並行取得:
   a. M7 PL集計 → 第1表欄にマッピング
   b. M7 BS集計 → 第3表欄にマッピング
   c. M6 固定資産台帳 → 減価償却明細を生成
   d. M7 月別売上 → 売上高500を12ヶ月分抽出
4. BlueReturnData DTO に集約してレスポンス
5. BlueReturnPreview.vue がタブ形式で各様式を表示
6. 利用者が「CSV ダウンロード」→ フロントで CSV 変換してダウンロード
```

### 8.3 決算整理仕訳生成フロー(減価償却)

```
1. 利用者が ClosingWizard.vue で「減価償却計上」を選択
2. closingTax.ts が GET /api/closing/blue-return?fiscal_year=2025 で減価償却明細を確認
3. 利用者が明細を確認し「仕訳を登録」をクリック
4. closingTax.ts が POST /api/closing/adjustments (type="depreciation") を送信
5. ClosingTaxService が固定資産ごとに JournalEntry を生成:
   借方: 減価償却費609 / 貸方: 工具器具備品150 (または対象資産科目)
   source = "closing-adjustment", fiscal_year = 2025
6. 仕訳ストアに保存し、登録済み JournalEntry を返す
7. ClosingWizard.vue が完了メッセージを表示し次ステップへ
```

## 9. 非機能設計方針

| 由来 | 観点 | 方針 |
|------|------|------|
| REQ-101, N-5 | 法令対応 | 税区分コード・みなし仕入率はマスタ定義に基づき、ハードコードしない |
| REQ-102, N-6 | 改定追従 | `TaxCategory.rate_percent` / `business_type` のマスタ変更のみで税率・みなし仕入率を更新できる設計 |
| REQ-103, N-8 | 出力形式 | CSV はフロントで変換(依存ライブラリを最小化)、PDF は TBD |
| REQ-104, N-7 | 監査性 | 消費税集計レスポンスに `journal_line_ids` を含め集計根拠を追跡可能にする |
| REQ-106, N-1 | 性能 | 消費税集計は仕訳明細のフルスキャンで実装(MVP)。ボトルネック時はインデックスまたは事前集計テーブルで対応 |

## 10. 依存モジュールと並列開発DAGにおける位置づけ

全体基本設計 §6 の並列開発DAG上の位置:

```
Layer 0: M1 core-masters, M2 journal (仕訳ストア)
Layer 1: M3 receivables, M4 expenses, M5 cash-bank, M6 fixed-assets
Layer 2: M7 reports (PL/BS/月別集計)
Layer 3: M8 closing-tax  ← 本モジュール (M6・M7 完了後に開発開始)
```

- M6(F-602): 固定資産台帳・減価償却計算明細のAPIが必要(REQ-001, REQ-012)。
- M7(F-704/705/707): PL・BS・月別売上のAPIが必要(REQ-010〜013)。
- M2(F-101): 仕訳登録APIへの書き込みが必要(REQ-001〜005, REQ-033)。
- M1(F-204): TaxCategory マスタ(T10/T08, business_type=5)の参照が必要(REQ-030〜032)。

## 11. 残課題 (TBD)

- [ ] PDF 出力ライブラリの選定(ブラウザ印刷 / WeasyPrint / フロントPDFライブラリ)(REQ-021)
- [ ] 複数事業区分への対応設計詳細(business_type 別みなし仕入率管理)(REQ-032, 全体BD §9)
- [ ] e-Tax 連携の詳細仕様(将来フェーズ)(REQ-022, 全体BD §9)
- [ ] 消費税中間納付の仕訳・集計への影響
- [ ] 青色申告65万控除の優良電子帳簿要件チェックの具体的実装(REQ-014)
- [ ] `GET /api/reports/pl` / `GET /api/reports/bs` / `GET /api/reports/monthly` のM7 API確定待ち(結合タイミング)

## 変更履歴

> 作成・更新のたびに概要を1行追記する (追記のみ。過去行は消さない)。

| 版 | 日付 | 変更概要 | 担当 |
|----|------|---------|------|
| 1.0 | 2026-06-22 | 初版作成 | Itou Hideki |
