---
name: coding-standards
description: アプリのソースコードの命名規則・仕様コメント(docstring/TSDoc)・フォーマットの規約。コードを書く/レビューするときに参照・適用する。「命名規則」「コメント追加」「コーディング規約」「フォーマット」などで起動。
---

# coding-standards

アプリのソースコードの**命名・仕様コメント・フォーマット**の規約。
ベストプラクティス (PEP 8 / PEP 257 / Google Python Style / Vue.js 公式スタイルガイド / TypeScript 命名規約) に準拠し、本プロジェクト向けに具体化する。

> 原則: **一貫性が最優先**。名前は説明的に (コメント不要なほど)。コメントは「何を」でなく**「なぜ」**を書く。整形は自動ツールに委譲する。

## 1. 命名規則

### Python (backend) — PEP 8
| 対象 | 規則 | 例 |
|------|------|----|
| 関数・変数・メソッド | `snake_case` | `get_user`, `item_id` |
| クラス・Pydanticモデル・例外 | `PascalCase` | `UserResponse`, `NotFoundError` |
| 定数 | `UPPER_SNAKE_CASE` | `MAX_RETRY` |
| モジュール・パッケージ | 短い `snake_case` | `users.py` |
| 非公開 | 先頭 `_` | `_next_id`, `_store` |
| FastAPI ルーター | `prefix` はリソース複数形 | `APIRouter(prefix="/users")` |
| Pydanticモデル | 役割を接尾辞に | `UserCreate` / `UserResponse` |
- `l` `O` `I` の単独名は避ける。型ヒントは必須 (`Any` 回避)。

### TypeScript / Vue (frontend)
| 対象 | 規則 | 例 |
|------|------|----|
| 変数・関数 | `camelCase` | `listUsers`, `newTitle` |
| 型・インターフェース・enum・クラス | `PascalCase` | `User`, `TaskStatus` |
| インターフェースのメンバ | `camelCase` | `id`, `createdAt` |
| 定数 (モジュール定数) | `UPPER_SNAKE_CASE` | `BASE_URL` |
| Vue コンポーネント | **多語** PascalCase (root の `App` は例外) | `UsersList.vue` |
| コンポーネントファイル | `PascalCase.vue` | `TaskCard.vue` |
| service ファイル | `camelCase.ts` | `users.ts` |
| composable | `useXxx` | `useFetch` |
| Base/汎用部品 | `Base`/`App`/`V` 接頭辞 | `BaseButton.vue` |
- **`I` 接頭辞・`Interface` 接尾辞は使わない** (`IUser`/`UserInterface` 禁止)。
- props/emits は JS では `camelCase`、DOM テンプレートでは `kebab-case`。

## 2. 仕様コメント

### 付与基準
- **公開**モジュール/関数/クラス/メソッドには docstring (Python) / TSDoc (TS) を付ける。
- 非公開や自明なものは不要。必要なら短い行コメントで「なぜ」を補う。
- コメントは実装と**同期**を保つ (古いコメントは害)。

### Python — Google スタイル docstring
- `"""` 三重引用符。要約は1行 (〜72字) で句点終わり。
- 引数/戻り値/例外が非自明なら `Args:` / `Returns:` / `Raises:` を書く。
```python
def create_task(body: TaskCreate) -> TaskResponse:
    """タスクを1件追加して返す。

    由来: REQ-002 / SPEC-102 / DD-002

    Args:
        body: 追加するタスク (title は 1〜100 文字)。

    Returns:
        採番済みの TaskResponse。

    Raises:
        HTTPException: title が制約違反のとき 422。
    """
```

### TypeScript — TSDoc
```ts
/**
 * ユーザー一覧を取得する。
 * 由来: REQ-001 / SPEC-101
 * @returns ユーザー配列。非 2xx は Error を throw。
 */
export async function listUsers(): Promise<User[]> { ... }
```

### 工程ID の紐づけ (本プロジェクト独自)
- 仕様に対応するコードの docstring/コメントに **`由来: REQ-xxx / SPEC-xxx / DD-xxx`** を任意で記載し、
  `write-dev-docs` の工程ドキュメントとコードを相互に辿れるようにする。

## 3. フォーマット (自動ツールに委譲・再記述しない)
- **Python**: `ruff format` (整形) + `ruff check` (lint)。行長 100、import 並び替えは ruff isort (`I`)。
- **TS/Vue**: `prettier` (整形) + `eslint` (lint)。整形ルールは `eslint-config-prettier` で Prettier に一本化。
- コミット前に必ず通す: `ruff check . && ruff format --check .` / `npm run lint && npm run type-check`。

## 4. 機械強制 (CI/lint で自動チェック)
- **Python (ruff)**: `N` (pep8-naming) と `D` (pydocstyle, convention=google) を有効化。
  - 公開クラス/メソッド/関数に docstring 必須 (D101/D102/D103)。モジュール/パッケージ/`__init__` の docstring は不要 (D100/D104/D107 は ignore)。
  - `tests/**` は docstring 免除。
- **TS (eslint)**: `@typescript-eslint/naming-convention` で型は PascalCase、`I` 接頭辞インターフェースを禁止。

## ガードレール
- 識別子 (名前) は**英語**、docstring/コメントは**日本語**で書く。
- `I` 接頭辞インターフェース・`Any`・グローバル CSS を増やさない。
- 整形/命名は手で直さずツール (`ruff`/`prettier`/`eslint`) に任せ、CI を緑に保つ。
- 既存コードに合わせる (一貫性優先)。規約変更は本 SKILL と lint 設定の両方を更新する。

## 出典
- PEP 8 / PEP 257 (peps.python.org), Google Python Style Guide, Vue.js 公式スタイルガイド (vuejs.org/style-guide), TypeScript 命名規約のベストプラクティス。
