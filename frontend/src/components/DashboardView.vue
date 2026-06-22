<script setup lang="ts">
/**
 * ダッシュボード (M7 F-706)。売上・利益・現預金残高・未入金を数値カードで可視化する。
 */
import { ref, onMounted, watch } from "vue";
import { fetchDashboard, type Dashboard } from "@/services/accounting";

const props = defineProps<{ reloadKey: number }>();
const data = ref<Dashboard | null>(null);

async function load() {
  data.value = await fetchDashboard();
}

onMounted(load);
watch(() => props.reloadKey, load);
</script>

<template>
  <section v-if="data" class="cards">
    <div class="card">
      <span class="label">当期売上高</span>
      <span class="value">¥{{ data.revenueTotal.toLocaleString() }}</span>
    </div>
    <div class="card" :class="{ profit: data.netIncome >= 0, loss: data.netIncome < 0 }">
      <span class="label">当期純利益</span>
      <span class="value">¥{{ data.netIncome.toLocaleString() }}</span>
    </div>
    <div class="card">
      <span class="label">現預金残高</span>
      <span class="value">¥{{ data.cashBalance.toLocaleString() }}</span>
    </div>
    <div class="card">
      <span class="label">未入金 (売掛金)</span>
      <span class="value">¥{{ data.receivablesBalance.toLocaleString() }}</span>
    </div>
  </section>
</template>

<style scoped>
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}
.card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.card .label {
  color: #6b7280;
  font-size: 0.9rem;
}
.card .value {
  font-size: 1.8rem;
  font-weight: bold;
}
.card.profit .value {
  color: #16a34a;
}
.card.loss .value {
  color: #b91c1c;
}
</style>
