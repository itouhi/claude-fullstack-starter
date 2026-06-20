---
feature: <機能名>
phase: 05-implementation
upstream:
  - ./04-detailed-design.md
status: draft
---

# 実装内容書 — <機能名>

> 詳細設計 (DD-xxx) をどう実装したかの記録。実装コードとテストコードの所在・要点をまとめる。
> 実装作業そのものは add-api-endpoint / add-vue-component / add-fullstack-feature スキルで行い、その結果をここに記録する。

## 1. 実装サマリ
| ID | 実装対象 | ファイル | 由来 (DD) | 状態 |
|----|---------|---------|----------|------|
| IMP-001 | `get_users` | `backend/app/api/users.py` | DD-001 | done |
| IMP-002 | `UsersList.vue` | `frontend/src/components/UsersList.vue` | DD-005 | done |

## 2. 主要な実装ポイント
### IMP-001 — <概要>
- <設計との差分や判断 (なぜそうしたか)。設計通りなら「設計通り」と明記>
- 関連コミット / PR: <ハッシュ or #番号>

## 3. テストコード
> 新規エンドポイントには最低 1 件のテストを書く (CLAUDE.md)。各テストが検証する仕様 ID を示す。

| テスト ID | テスト関数 | ファイル | 検証対象 (DD/SPEC) | 種別 |
|----------|-----------|---------|-------------------|------|
| TST-001 | `test_get_users_ok` | `backend/tests/test_users.py` | DD-001 / SPEC-101 | 正常系 |
| TST-002 | `test_get_users_404` | `backend/tests/test_users.py` | DD-004 / SPEC-101 | 異常系 |

## 4. 品質チェック結果
| チェック | コマンド | 結果 |
|---------|---------|------|
| Lint/Format | `ruff check . && ruff format --check .` | <pass/fail> |
| 型チェック (FE) | `npm run type-check` | <pass/fail> |
| テスト | `pytest -q` | <件数 / pass-fail> |

## 5. 設計からの逸脱・残課題
- <設計と異なる実装をした点とその理由>
- [ ] <TODO / 技術的負債>

## 6. 動作確認
> 型チェック・テストのパスだけで「完了」としない (CLAUDE.md)。ブラウザ確認の有無を記録。
- <ブラウザでの確認内容 / スクリーンショット参照>

## 変更履歴
> 作成・更新のたびに概要を1行追記する (追記のみ。過去行は消さない)。

| 版 | 日付 | 変更概要 | 担当 |
|----|------|---------|------|
| 1.0 | <YYYY-MM-DD> | 初版作成 | <名前> |
