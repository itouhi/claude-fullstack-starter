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
    <v-card class="card" variant="outlined">
      <v-card-subtitle class="label">当期売上高</v-card-subtitle>
      <v-card-title class="value">¥{{ data.revenueTotal.toLocaleString() }}</v-card-title>
    </v-card>
    <v-card class="card" :class="{ profit: data.netIncome >= 0, loss: data.netIncome < 0 }" variant="outlined">
      <v-card-subtitle class="label">当期純利益</v-card-subtitle>
      <v-card-title class="value">¥{{ data.netIncome.toLocaleString() }}</v-card-title>
    </v-card>
    <v-card class="card" variant="outlined">
      <v-card-subtitle class="label">現預金残高</v-card-subtitle>
      <v-card-title class="value">¥{{ data.cashBalance.toLocaleString() }}</v-card-title>
    </v-card>
    <v-card class="card" variant="outlined">
      <v-card-subtitle class="label">未入金 (売掛金)</v-card-subtitle>
      <v-card-title class="value">¥{{ data.receivablesBalance.toLocaleString() }}</v-card-title>
    </v-card>
  </section>
</template>

<style scoped>
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}
.card .label {
  color: #6b7280;
  font-size: 0.9rem;
}
.card .value {
  font-size: 1.8rem;
  font-weight: bold;
  white-space: normal;
}
.card.profit .value {
  color: #16a34a;
}
.card.loss .value {
  color: #b91c1c;
}
</style>
