---
name: add-store
description: frontend に Pinia で状態管理を導入・追加する。機能単位の store (useXxxStore) で共有状態・サーバ状態を整理する。「状態管理」「Pinia」「ストア」「グローバルstate」などで起動。
---

# add-store

frontend の共有状態を **Pinia** (Vue 公式推奨) で管理する。
コンポーネント内 `ref` で足りるうちは導入せず、**複数コンポーネントで共有・複雑化したら**入れる。

> 出典: Pinia は Vue コア推奨。store は**データ種別でなく機能単位**でまとめる (djamware.com, dev.to)。

## 初回セットアップ
1. `npm i pinia`。
2. `main.ts`: `import { createPinia } from "pinia"` → `app.use(createPinia())`。
3. `src/stores/` を作成。

## store の書き方 (機能単位・Composition 形式)
```ts
// src/stores/tasks.ts
import { defineStore } from "pinia";
import { ref } from "vue";
import { listTasks, createTask, type Task } from "@/services/tasks";

/** タスクの共有状態。由来: SPEC-001/002 */
export const useTasksStore = defineStore("tasks", () => {
  const items = ref<Task[]>([]);
  const loading = ref(false);

  async function load() {
    loading.value = true;
    try {
      items.value = await listTasks();
    } finally {
      loading.value = false;
    }
  }
  async function add(title: string) {
    await createTask(title);
    await load();
  }
  return { items, loading, load, add };
});
```
- 命名: `useXxxStore` / id は機能キー。
- **API 通信は `services/` に残す**。store はそれを呼んで状態を保持する (責務分離)。

## 役割の線引き
- ローカル UI 状態 (フォーム入力など) → コンポーネントの `ref` のまま。
- 画面跨ぎ/共有/サーバ状態 → store。
- compose-service のサービスでは、機能横断の共有 (ログインユーザー等) を store に置くと整理しやすい。

## ガードレール
- 小さく始める: 必要になった状態だけ store 化 (過剰な共有 state を作らない)。
- store は機能単位。データ種別 (例 "all data") で1つにまとめない。
- テスト (`add-frontend-test`) では各テスト前に `setActivePinia(createPinia())` で初期化。
- 命名・型・docstring は `coding-standards`。`Any` 回避、型を付ける。
