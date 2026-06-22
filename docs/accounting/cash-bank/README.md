# cash-bank (資金管理) — ドキュメント索引

M5 `cash-bank` モジュールの開発工程ドキュメント一覧。

| # | 工程 | ファイル | 状態 |
|---|------|---------|------|
| 01 | 要求事項 | [01-requirements.md](./01-requirements.md) | draft |
| 02 | 仕様書 | — | 未作成 |
| 03 | 基本設計 | [03-basic-design.md](./03-basic-design.md) | draft |
| 04 | 詳細設計 | — | 未作成 |
| 05 | 実装内容 | — | 未作成 |
| 06 | テスト計画 | — | 未作成 |
| 07 | テスト結果 | — | 未作成 |
| 08 | リリース | — | 未作成 |

## 関連ドキュメント

- [全体基本設計書](../00-overall-basic-design.md) — アーキテクチャ・共通データモデル・並列開発計画
- M1 `core-masters`: 勘定科目マスタ・期首残高（上流依存）
- M2 `journal`: 仕訳エンジン・仕訳ストア（上流依存）
- M7 `reports`: 帳簿レポート（出納帳データを共有）

## 機能スコープ

| 機能 | 優先度 | F-ID |
|------|--------|------|
| F-501 現金出納帳 | Must | 01-requirements REQ-001〜004 |
| F-502 預金出納帳 | Must | 01-requirements REQ-011〜013 |
| F-102/N-9 簡易入力 | Must | 01-requirements REQ-021〜024 |
| F-503 CSV明細取込 | Should | 01-requirements REQ-031〜034 |
| F-504 消込・名寄せ | Should | 01-requirements REQ-041〜043 |
