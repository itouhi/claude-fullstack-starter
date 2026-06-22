# data-io — ドキュメント索引

M9 `data-io` (データ入出力・連携) モジュールの開発ドキュメント一覧。

上位文書: [全体基本設計書](../00-overall-basic-design.md)

| # | 工程 | ファイル | ステータス |
|---|------|---------|-----------|
| 01 | 要求事項定義 | [01-requirements.md](./01-requirements.md) | draft |
| 02 | 仕様書 | 02-spec.md | 未作成 |
| 03 | 基本設計 | [03-basic-design.md](./03-basic-design.md) | draft |
| 04 | 詳細設計 | 04-detailed-design.md | 未作成 |
| 05 | 実装内容 | 05-implementation.md | 未作成 |
| 06 | テスト計画 | 06-test-plan.md | 未作成 |
| 07 | テスト結果 | 07-test-results.md | 未作成 |
| 08 | リリース | 08-release.md | 未作成 |

## 担当機能 (F-ID)

| F-ID | 機能 | 優先度 | 対応 REQ |
|------|------|--------|---------|
| F-901 | CSVインポート（仕訳・明細の一括取込） | Should | REQ-001〜006 |
| F-902 | CSV/PDFエクスポート（帳簿・決算書） | Must | REQ-011〜018 |
| F-903 | バックアップ/復元 | Must | REQ-021〜026 |
| F-904 | 年度繰越（期末残高→翌期首残高） | Must | REQ-031〜036 |
