---
feature: fixed-assets
phase: 03-basic-design
upstream:
  - ../00-overall-basic-design.md
  - ./01-requirements.md
status: draft
---

# 基本設計書 — fixed-assets (固定資産・減価償却)

> 全体基本設計書 (`00-overall-basic-design.md`) の共通決定事項 (レイヤ構造・仕訳契約・API規約) を前提とする。本書はモジュール固有の構造を決める。

## 1. アーキテクチャ概要

M6 `fixed-assets` は「仕訳を作る側」(Layer 1) に位置する。固定資産台帳を保持し、減価償却計算サービスが年間償却費を算出して `JournalEntry` を生成する。M8 `closing-tax` (決算整理) から呼び出されることで、決算整理仕訳として計上される。

```
[ブラウザ SPA]
  FixedAssetList.vue / FixedAssetForm.vue / DepreciationSchedule.vue
  │  src/services/fixedAssets.ts  (型付き API クライアント)
  ▼  /api/fixed-assets/*
[BFF / API]  app/api/fixed_assets.py
  │  app/services/depreciation_service.py  (減価償却計算・仕訳生成)
  ▼
[ドメイン層]
  app/domain/fixed_asset.py     ←  FixedAsset エンティティ + DepreciationMethod
  app/domain/journal.py         ←  JournalEntry / JournalLine (共通基盤 M2)
  ▼
[永続化層 (in-memory → add-persistence で DB 化)]
  store.py の AccountingStore に fixed_assets dict を追加
```

M8 `closing-tax` との連携:
```
M8 決算整理サービス
  → POST /api/fixed-assets/{id}/depreciation  (当期償却の仕訳計上を依頼)
  ← 生成された JournalEntry を返す
M8 はこの仕訳 ID を決算整理仕訳の一部として集約する
```

## 2. コンポーネント構成

| ID | コンポーネント | 役割 | 配置 | 由来 |
|----|--------------|------|------|------|
| BD-001 | `FixedAssetList.vue` | 固定資産台帳一覧 (資産名・取得日・取得価額・未償却残高・償却累計) | `frontend/src/components/fixed-assets/` | REQ-002 |
| BD-002 | `FixedAssetForm.vue` | 固定資産の新規登録フォーム (少額特例の自動判定表示含む) | `frontend/src/components/fixed-assets/` | REQ-001 / REQ-021 |
| BD-003 | `DepreciationSchedule.vue` | 年度別償却予定表 (期首残高・当期償却額・期末残高の一覧) | `frontend/src/components/fixed-assets/` | REQ-004 |
| BD-004 | `fixedAssets.ts` | API クライアント (台帳 CRUD・償却スケジュール取得・仕訳計上) | `frontend/src/services/` | REQ-001〜023 |
| BD-005 | `fixed_asset.py` (ドメイン) | `FixedAsset` エンティティ・`DepreciationMethod` 列挙・`DepreciationEntry` 値オブジェクト | `backend/app/domain/` | REQ-001 / REQ-011 |
| BD-006 | `depreciation_service.py` | 減価償却計算ロジック (定額法・月割・少額特例・按分・仕訳生成) | `backend/app/services/` | REQ-011〜023 |
| BD-007 | `fixed_assets.py` (API ルーター) | FastAPI ルーター。台帳 CRUD / 償却スケジュール / 仕訳計上エンドポイント | `backend/app/api/` | REQ-001〜023 |

## 3. データ設計 (概念)

### 3.1 FixedAsset エンティティ

全体基本設計 §4 の `FixedAsset 固定資産` を詳細化する。金額は円単位の整数 (整数円 / 全体設計 §4)。

| 属性 | 型 | 必須 | 説明 | 由来 |
|------|----|----|------|------|
| `id` | int | ○ | 採番 ID | — |
| `name` | str | ○ | 資産名 (例: ノートPC、デスクチェア) | REQ-001 |
| `acquisition_date` | date | ○ | 取得日 (期中取得の月割計算の基点) | REQ-001 / REQ-012 |
| `acquisition_cost` | int | ○ | 取得価額 (円。正の整数) | REQ-001 |
| `useful_life_years` | int | ○ | 耐用年数 (年。1以上。少額特例時は1を設定) | REQ-001 |
| `depreciation_method` | DepreciationMethod | ○ | 償却方法 (現在: `straight_line` のみ) | REQ-001 |
| `business_use_ratio` | float | ○ | 事業専用割合 (0.01〜1.00。家事按分なし=1.0) | REQ-001 / REQ-014 |
| `is_small_amount_special` | bool | ○ | 少額特例適用フラグ (取得価額<30万円かつ青色) | REQ-021 |
| `book_value` | int | ○ | 未償却残高 (初期値=取得価額、償却計上ごとに更新) | REQ-016 |
| `accumulated_depreciation` | int | ○ | 償却累計額 (初期値=0、償却計上ごとに加算) | REQ-016 |
| `description` | str \| None | — | 摘要・備考 | REQ-001 |
| `status` | AssetStatus | ○ | `active` / `fully_depreciated` / `deleted` | REQ-101 |
| `created_at` | datetime | ○ | 登録日時 | N-7 |
| `updated_at` | datetime | ○ | 最終更新日時 | N-7 |

```
DepreciationMethod (enum): STRAIGHT_LINE = "straight_line"  # 定額法
AssetStatus (enum)       : ACTIVE = "active" / FULLY_DEPRECIATED = "fully_depreciated" / DELETED = "deleted"
```

### 3.2 DepreciationEntry 値オブジェクト (償却スケジュール1行)

計算結果の表示・返却に用いる。DB 永続化は不要 (FixedAsset から都度算出)。

| 属性 | 型 | 説明 |
|------|----|----|
| `fiscal_year` | int | 対象年度 |
| `opening_book_value` | int | 期首未償却残高 |
| `depreciation_amount` | int | 当期事業按分後償却費 (仕訳計上額) |
| `business_depreciation` | int | 借方 減価償却費609 計上額 |
| `private_depreciation` | int | 借方 事業主貸410 振替額 (家事按分分) |
| `closing_book_value` | int | 期末未償却残高 |

### 3.3 ストア拡張

`backend/app/store.py` の `AccountingStore` に `fixed_assets: dict[int, FixedAsset]` と採番カウンタを追加する。永続化は将来 `add-persistence` で DB 化する。

## 4. インターフェース設計

### 4.1 API エンドポイント

全体基本設計 §5 の API 規約に準拠 (prefix は `main.py` 一括付与 `/api`、`response_model` 必須)。

| ID | メソッド | パス | 概要 | 由来 |
|----|---------|------|------|------|
| BD-101 | GET | `/api/fixed-assets` | 固定資産台帳一覧 (deleted 除外) | REQ-002 |
| BD-102 | POST | `/api/fixed-assets` | 固定資産新規登録 (少額特例判定・初期値計算含む) | REQ-001 / REQ-021 |
| BD-103 | GET | `/api/fixed-assets/{id}` | 固定資産詳細取得 | REQ-002 |
| BD-104 | PATCH | `/api/fixed-assets/{id}` | 固定資産情報修正 (摘要・事業専用割合) | REQ-003 |
| BD-105 | GET | `/api/fixed-assets/{id}/depreciation-schedule` | 年度別償却予定表の取得 | REQ-004 |
| BD-106 | POST | `/api/fixed-assets/{id}/depreciation` | 指定年度の減価償却仕訳計上 (M8 から呼び出し) | REQ-015 / REQ-016 |

リクエスト/レスポンスの詳細スキーマは詳細設計 (04-detailed-design.md) で定義する。

### 4.2 フロントエンド サービス

`frontend/src/services/fixedAssets.ts` に以下の関数を集約する (コンポーネントから直接 fetch しない)。

| 関数名 | 概要 | 由来 |
|--------|------|------|
| `listFixedAssets()` | 台帳一覧取得 | BD-101 |
| `createFixedAsset(data)` | 新規登録 | BD-102 |
| `getFixedAsset(id)` | 詳細取得 | BD-103 |
| `updateFixedAsset(id, data)` | 情報修正 | BD-104 |
| `getDepreciationSchedule(id)` | 償却スケジュール取得 | BD-105 |
| `postDepreciation(id, fiscalYear)` | 当期償却仕訳計上 | BD-106 |

## 5. 処理フロー (主要シナリオ)

### 5.1 固定資産登録

```
1. ユーザーが FixedAssetForm.vue に資産名・取得日・取得価額・耐用年数・事業専用割合を入力
2. 取得価額が30万円未満 → 少額特例適用の選択肢を表示 (REQ-021)
3. 「登録」ボタン → fixedAssets.ts の createFixedAsset() → POST /api/fixed-assets
4. API: DepreciationService が少額特例フラグ・初期未償却残高を設定し FixedAsset レコードを生成
5. ストアに保存し、生成された FixedAsset を返す
6. 一覧画面へ遷移して新しい資産が表示される
```

### 5.2 減価償却計算・仕訳計上

```
1. ユーザーまたは M8 決算整理サービスが POST /api/fixed-assets/{id}/depreciation?fiscal_year=2025 を呼び出す
2. DepreciationService が FixedAsset を取得
3. 当期償却費を計算 (詳細は §6 参照)
4. 家事按分: 事業按分後償却費 = 計算償却費 × business_use_ratio (切り捨て)
5. 仕訳生成 (§5.3 参照)
6. 生成した JournalEntry を仕訳エンジン (M2) 経由でストアに保存
7. FixedAsset の book_value・accumulated_depreciation を更新
8. JournalEntry を返す
```

### 5.3 仕訳生成パターン

#### パターンA: 家事按分なし (business_use_ratio = 1.0)

```
借方: 減価償却費 (609)   [事業按分後償却費]
貸方: 工具器具備品 (150) [事業按分後償却費]
```

#### パターンB: 家事按分あり (business_use_ratio < 1.0)

```
借方: 減価償却費 (609)   [年間償却費 × 事業専用割合 (切り捨て)]
借方: 事業主貸 (410)     [年間償却費 × (1 − 事業専用割合) (切り捨て)]
貸方: 工具器具備品 (150) [借方合計 = 年間償却費全額]

※ 端数調整: 貸方合計 = 年間償却費全額。借方の事業主貸は「年間償却費 − 減価償却費計上額」とする
  ことで借貸の一致 (JournalEntry の不変条件) を保証する
```

摘要例: `「パソコン (2024年取得) 2025年度減価償却」`

## 6. 減価償却計算ロジック (確定)

### 6.1 定額法の基本計算

```
年間償却費 = floor(取得価額 × (1 / 耐用年数))
           = floor(取得価額 / 耐用年数)   ← 円未満切り捨て
```

### 6.2 期中取得の月割計算

取得年度の償却費は取得月から12月 (期末) までの月数で按分する。

```
取得年度の償却費 = floor(年間償却費 × 取得月から期末までの月数 / 12)

取得月からの月数 = 12 − 取得月 + 1
例: 取得月が4月 (4月) → 月数 = 12 − 4 + 1 = 9 ヶ月
```

### 6.3 最終年度の備忘価額1円残し

```
if 期首未償却残高 − 年間償却費 <= 1:
    当期償却費 = 期首未償却残高 − 1   # 備忘価額1円を残す
else:
    当期償却費 = 年間償却費 (または月割償却費)
```

### 6.4 少額特例 (取得価額 < 30万円 かつ 青色申告)

```
取得年度の償却費 = 取得価額 − 1   # 取得年度に全額即時償却、備忘1円残し
翌年度以降      = 0 円            # 翌年度以降は計上なし (資産は台帳に残す)
```

### 6.5 数値例 (定額法・期中取得)

**前提条件**
- 資産名: ノートPC
- 取得価額: 300,000 円
- 取得日: 2025年4月1日 (4月取得)
- 耐用年数: 5年
- 事業専用割合: 1.0 (家事按分なし)
- 少額特例: 非適用 (取得価額 = 30万円 ちょうど、30万円未満でないため不可)

**計算過程**

> **注 (v1.1 訂正):** 旧版は最終年度を2029年度・74,999円としていたが、これは §6.3 の
> ルール (「期首残高 − 年間償却費 ≤ 1 のときに備忘1円を残す」) と矛盾していた。期中取得
> (月割) により未償却分が耐用年数を1年超えて翌2030年度に残るのが定額法の正しい挙動。
> §6.3 のルールに従い、以下のとおり訂正する (実装 `services/depreciation.py` と一致)。

| 年度 | 期首残高 | 計算 | 当期償却費 | 期末残高 |
|------|---------|------|-----------|---------|
| 2025 (取得) | 300,000 | floor(60,000 × 9/12) | 45,000 | 255,000 |
| 2026 | 255,000 | 満年 | 60,000 | 195,000 |
| 2027 | 195,000 | 満年 | 60,000 | 135,000 |
| 2028 | 135,000 | 満年 | 60,000 | 75,000 |
| 2029 | 75,000 | 満年 (75,000 − 60,000 = 15,000 > 1) | 60,000 | 15,000 |
| 2030 (最終) | 15,000 | 15,000 − 1 (備忘1円残し) | 14,999 | 1 |

**2025年度 仕訳 (パターンA)**
```
借方: 減価償却費 (609)   45,000 円
貸方: 工具器具備品 (150) 45,000 円
摘要: ノートPC (2025年取得) 2025年度減価償却
```

**少額特例の別例 (取得価額: 150,000 円、取得日: 2025年7月)**

| 項目 | 計算 | 結果 |
|------|------|------|
| 少額特例判定 | 150,000 < 300,000 → 適用可 | 選択可 |
| 取得年度 即時償却費 | 150,000 − 1 | 149,999 円 |
| 翌年度以降 | 0 円 (残高1円のみ台帳保持) | — |

## 7. UI 設計方針

| 画面 / コンポーネント | 表示内容 | 由来 |
|---------------------|---------|------|
| `FixedAssetList.vue` | 台帳一覧: 資産名・取得日・取得価額・未償却残高・償却累計・ステータス。詳細/償却予定表へのリンク | REQ-002 / BD-001 |
| `FixedAssetForm.vue` | 登録フォーム: 各入力フィールド。取得価額入力時に少額特例の適用可否を即時表示 (30万円未満なら「少額特例を適用する」チェックボックスを表示) | REQ-001 / REQ-021〜022 / BD-002 |
| `DepreciationSchedule.vue` | 年度別償却予定表: 年度・期首残高・当期償却費 (事業分)・家事按分分・期末残高の表形式表示 | REQ-004 / BD-003 |

- 画面上では「借方/貸方」を前面に出さず、「固定資産を登録する」「減価償却を計上する」等の業務用語を使用する (REQ-104 相当、全体 N-9)
- `<script setup lang="ts">` + Composition API で統一 (CLAUDE.md 規約)

## 8. 並列開発上の結合点

全体基本設計 §6.1 の「仕訳契約による分離」に基づく結合点:

| 結合先 | 契約 | 方向 | 備考 |
|--------|------|------|------|
| M2 `journal` | `JournalEntry` / `JournalLine` の生成・`POST /api/journal-entries` 相当のストア書き込み | M6 → M2 | M2 が先行して稼働していること (前提) |
| M1 `core-masters` | 勘定科目コード 150 / 609 / 410 が `AccountingStore.accounts` に存在すること | M6 → M1 | `store.py` 標準マスタで確認済み |
| M8 `closing-tax` | `POST /api/fixed-assets/{id}/depreciation` を M8 決算整理から呼び出す | M8 → M6 | M6 API の安定が先行条件 |
| M7 `reports` | 仕訳ストアを読み取り専用で参照 (直接結合なし) | M7 → M2 (仕訳) | M6 は仕訳を生成するだけ。M7 との直接依存なし |

## 9. 非機能設計方針

| 由来 | 観点 | 方針 |
|------|------|------|
| REQ-101 / N-2 | データ保全 | 固定資産の物理削除禁止。`status = deleted` の論理管理。償却計上で `book_value` を不変更新 |
| REQ-102 / N-6 | 税制改定追従 | 耐用年数と1/耐用年数の計算はサービス層に局所化。マスタ化は `add-persistence` 後に対応 (TBD) |
| REQ-103 / N-7 | 操作ログ | `add-observability` の共通デコレータで固定資産の登録・修正・償却計上を監査ログへ記録 |
| REQ-104 | 計算確定性 | 全計算を純関数として実装。入力 (取得価額/耐用年数/取得日/年度) が同じなら結果が必ず同一 |

## 10. 未決事項 (TBD)

- [ ] 定率法の基本設計: `DepreciationMethod` に `DECLINING_BALANCE` を追加する場合の計算式 (将来)
- [ ] 固定資産の売却・除却処理 (除却損仕訳の生成、ステータス管理) の設計
- [ ] 耐用年数マスタの永続化設計 (`add-persistence` 導入後に対応)
- [ ] 年度途中での事業専用割合変更の設計 (現状は台帳登録時の値を固定で使用)

## 変更履歴

> 作成・更新のたびに概要を1行追記する (追記のみ。過去行は消さない)。

| 版 | 日付 | 変更概要 | 担当 |
|----|------|---------|------|
| 1.0 | 2026-06-22 | 初版作成 | Itou Hideki |
| 1.1 | 2026-06-22 | §6.5 の数値例を §6.3 ルールと整合するよう訂正 (最終年度2030・14,999円。実装と一致) | Itou Hideki |
