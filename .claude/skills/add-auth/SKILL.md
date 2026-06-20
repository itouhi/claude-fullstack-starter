---
name: add-auth
description: 本格的な認証・認可を導入する。JWT (アクセス+リフレッシュ)、パスワードハッシュ、ロールベースアクセス制御 (RBAC)、レート制限。固定トークンのサンプル実装を置換する。「認証」「ログイン」「JWT」「権限」「RBAC」などで起動。
---

# add-auth

固定トークンのサンプル認証を、**本番水準の認証・認可**に置き換える。

> 出典: FastAPI best practices — JWT/RBAC/rate limit (auth0.com), Web app security checklist (stackhawk.com / OWASP Top 10)。

## 導入するもの
- **JWT**: 短命のアクセストークン + リフレッシュトークン。
- **パスワード**: `passlib[bcrypt]` 等でハッシュ保存 (平文禁止)。
- **依存性**: `get_current_user` を `Depends` で注入し、保護エンドポイントに付与。
- **RBAC**: ロール (例 `admin`/`user`) を権限チェックの依存性で表現。
- **レート制限**: ログイン等の濫用防止 (slowapi 等)。

## 手順
1. 依存追加: `python-jose[cryptography]` (or `pyjwt`), `passlib[bcrypt]`。`Settings` に `jwt_secret`, 失効時間。
2. `app/auth/` に:
   - `security.py`: ハッシュ/検証、JWT 発行/検証。
   - `deps.py`: `get_current_user()` / `require_role("admin")` (依存性)。
3. エンドポイント: `POST /auth/login` (資格情報→トークン), `POST /auth/refresh`。
4. 保護: 既存ルーターの `require_token` を `Depends(get_current_user)` / `Depends(require_role(...))` に置換。
5. frontend: トークンを安全に保持 (httpOnly cookie が理想。`localStorage` は XSS リスク)。`services/` で `Authorization` ヘッダ付与・401 で再ログイン/リフレッシュ。
6. テスト: ログイン成功/失敗、未認証 401、権限不足 403、トークン期限切れ、リフレッシュ。
7. `verifier-webapp` でログイン→保護画面の導線を実機確認。

## ガードレール (セキュリティ)
- パスワードは必ずハッシュ。シークレット (`jwt_secret`) は `.env`/secrets、コミット禁止。
- 本番は HTTPS 前提。トークンは短命、リフレッシュで更新。失効/ログアウトを設計。
- 認可は**サーバ側で必ず検証** (フロントの出し分けだけに頼らない)。OWASP「Broken Access Control」に注意。
- 本番のエラーは詳細を漏らさない (→ `add-observability`)。
- 命名・docstring・テストは `coding-standards` / `add-api-endpoint` の規約に従う。
