<script setup lang="ts">
import { ref } from "vue";
import { fetchSum } from "@/services/api";

const a = ref(0);
const b = ref(0);
const result = ref<number | null>(null);
const error = ref<string | null>(null);
const loading = ref(false);

/** backend に加算を要求し、結果/エラー/ローディング状態を更新する。 */
async function calc(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    result.value = (await fetchSum(a.value, b.value)).result;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="sum-widget">
    <h2>Sum</h2>
    <label>a: <input v-model.number="a" type="number" /></label>
    <label>b: <input v-model.number="b" type="number" /></label>
    <button :disabled="loading" @click="calc">計算</button>
    <p v-if="loading">calculating...</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <p v-else-if="result !== null"><strong>result:</strong> {{ result }}</p>
  </section>
</template>

<style scoped>
.sum-widget {
  margin-top: 1rem;
}
.error {
  color: crimson;
}
</style>
