---
name: add-observability
description: 構造化ログ・本番安全なエラーハンドリング・基本メトリクスを導入する。JSON ログ (request_id 等)、本番では汎用エラー、RED 指標。「ログ」「可観測性」「エラーハンドリング」「監視」「observability」などで起動。
---

# add-observability

サービスの**挙動を観測可能**にする。構造化ログ・一貫したエラーハンドリング・基本メトリクスを入れる。

> 出典: 構造化ログ (JSON, request_id/user_id/severity) と RED 指標 (Rate/Errors/Duration) が標準
> (appsecmaster.net)。本番は debug を切り、詳細エラーを汎用化する (FastAPI prod ガイド)。

## ログ (構造化)
- **JSON ログ**を標準出力へ (集約しやすい)。各ログに一貫フィールド: `request_id`, `path`, `status`, `duration_ms`, `severity`。
- **機微情報を出さない** (パスワード/トークン/個人情報)。
- リクエスト毎に `request_id` を採番し、ミドルウェアでログ・レスポンスヘッダに付与。
```python
# 概念: ミドルウェアで request_id を採番し、structlog/標準 logging(JSON) で出力
```

## エラーハンドリング
- FastAPI の `exception_handler` で**一貫した形**に整形 (例 `{ "detail": ..., "request_id": ... }`)。
- **本番は汎用メッセージ** (内部例外・スタックを漏らさない)。開発のみ詳細表示。`debug` は本番で無効。
- 想定エラーは `HTTPException` (4xx)、想定外は 500 + ログに詳細を残す (レスポンスには出さない)。

## メトリクス (任意・段階導入)
- **RED**: リクエスト数 / エラー率 / レイテンシ。`prometheus-fastapi-instrumentator` 等で `/metrics`。
- フロントは Sentry 等でエラー/パフォーマンスを収集 (任意)。

## 手順
1. backend: ログ設定 (JSON formatter) を `app/logging.py` に集約し `main.py` で初期化。
2. `request_id` ミドルウェア + 例外ハンドラを追加。
3. `Settings` に `debug`/`log_level` を持たせ、本番で debug=false。
4. 機微情報がログに出ないことを確認。`verifier-webapp`/`setup-ci` と併用。

## ガードレール
- ログに**秘密情報を出さない**。出力前にマスク/除外。
- 本番のエラーレスポンスは詳細を漏らさない (`add-auth` のセキュリティと整合)。
- ログは構造化 (grep でなくフィールドで検索できる形)。
- 命名・docstring は `coding-standards`。
