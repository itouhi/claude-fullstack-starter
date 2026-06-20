---
name: add-vue-component
description: Scaffold a new Vue 3 SFC under frontend/src/components/ using <script setup lang="ts"> and Composition API. Triggers when the user asks to "add a component", "新しいコンポーネント", etc.
---

# add-vue-component

新しい Vue 3 コンポーネントを追加します。

## 入力として確認すること

1. **コンポーネント名** — PascalCase (例: `UserCard`, `TaskList`)
2. **配置場所** — デフォルト `frontend/src/components/`
3. **Props / Emits** のシグネチャ
4. **使用場所** — 親コンポーネントへの組み込みも行うか

## 手順

1. `frontend/src/components/<Name>.vue` を作成
2. 必ず `<script setup lang="ts">` を使用し、`defineProps<T>()` / `defineEmits<T>()` で型を定義
3. `<template>` は最小マークアップ、`<style scoped>` で局所スタイル
4. 親コンポーネントに組み込む場合は `import <Name> from "@/components/<Name>.vue"` を追加
5. `cd frontend && npm run type-check` で型チェック pass を確認
6. 画面に表示される変更は **`verifier-webapp` スキルで実ブラウザ確認**する (型チェックだけで完了としない / CLAUDE.md)

## テンプレート

```vue
<script setup lang="ts">
interface Props {
  title: string;
  count?: number;
}

const props = withDefaults(defineProps<Props>(), {
  count: 0,
});

const emit = defineEmits<{
  (e: "change", value: number): void;
}>();

function increment() {
  emit("change", props.count + 1);
}
</script>

<template>
  <article class="card">
    <h2>{{ title }}</h2>
    <p>count: {{ count }}</p>
    <button @click="increment">+1</button>
  </article>
</template>

<style scoped>
.card {
  border: 1px solid #ccc;
  padding: 1rem;
  border-radius: 8px;
}
</style>
```

## ガードレール

- Options API は使わない (Composition API + `<script setup>` 統一)
- Props/Emits は必ず TypeScript 型定義で表現する
- グローバル CSS を増やさない (`scoped` または CSS Modules)
- `any` の使用を避ける
- 命名・コメント (TSDoc)・フォーマットは `coding-standards` スキルに従う (型は PascalCase、`I` 接頭辞禁止、eslint naming で機械強制)
- 複数コンポーネントで共有する状態は `ref` で抱えず `add-store` スキル (Pinia) で管理する
