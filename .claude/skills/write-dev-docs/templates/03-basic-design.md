---
feature: <機能名>
phase: 03-basic-design
upstream:
  - ./02-spec.md
status: draft
---

# 基本設計書 — <機能名>

> 仕様 (SPEC-xxx) を実現するシステム全体の構造を決める。「どう作るか」のアーキテクチャ視点。

## 1. アーキテクチャ概要
<backend (FastAPI) / frontend (Vue 3) のどこに何を置くかの全体像。必要なら構成図 (ASCII でも可)>

```
[Vue Component] -> [src/services/*.ts] --/api--> [FastAPI router] -> [service/logic] -> [data]
```

## 2. コンポーネント構成
| ID | コンポーネント | 役割 | 配置 | 由来 (SPEC) |
|----|--------------|------|------|------------|
| BD-001 | <UsersList.vue> | <一覧表示> | `frontend/src/components/` | SPEC-001 |
| BD-002 | <users router> | <一覧 API> | `backend/app/api/users.py` | SPEC-101 |

## 3. データ設計 (概念)
| エンティティ | 主な属性 | 関連 | 永続化 (DB/in-memory) | 由来 |
|------------|---------|------|---------------------|------|
| <User> | id, name | — | in-memory (初期) | SPEC-101 |

## 4. インターフェース設計 (概要)
| ID | I/F | 概要 | 由来 |
|----|-----|------|------|
| BD-101 | フロント↔API | `/users` を fetch、`/api` は Vite proxy 経由 | SPEC-101 |

## 5. 処理フロー (主要シナリオ)
<正常系の流れを番号付きで。例: 1. 画面ロード → 2. service が GET /users → 3. 一覧描画>

## 6. 非機能設計方針
| 由来 (REQ/SPEC) | 観点 | 方針 |
|----------------|------|------|
| REQ-101 | 性能 | <キャッシュ/ページング方針> |

## 7. 未決事項 (TBD)
- [ ] <設計上の検討事項>

## 変更履歴
> 作成・更新のたびに概要を1行追記する (追記のみ。過去行は消さない)。

| 版 | 日付 | 変更概要 | 担当 |
|----|------|---------|------|
| 1.0 | <YYYY-MM-DD> | 初版作成 | <名前> |
