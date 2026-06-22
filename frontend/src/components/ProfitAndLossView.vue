<script setup lang="ts">
/**
 * 損益計算書 (M7 F-704)。収益・費用を集計し当期純利益を表示する。
 */
import { ref, onMounted, watch } from "vue";
import { fetchProfitAndLoss, type ProfitAndLoss } from "@/services/accounting";

const props = defineProps<{ reloadKey: number }>();
const pl = ref<ProfitAndLoss | null>(null);

async function load() {
  pl.value = await fetchProfitAndLoss();
}

onMounted(load);
watch(() => props.reloadKey, load);
</script>

<template>
  <div v-if="pl" class="pl">
    <v-table density="compact" class="pl-table">
      <tbody>
        <tr class="section">
          <th colspan="2">収益</th>
        </tr>
        <tr v-for="r in pl.revenues" :key="r.accountCode">
          <td>{{ r.accountName }}</td>
          <td class="num">{{ r.amount.toLocaleString() }}</td>
        </tr>
        <tr class="subtotal">
          <td>収益合計</td>
          <td class="num">{{ pl.totalRevenue.toLocaleString() }}</td>
        </tr>
        <tr class="section">
          <th colspan="2">費用</th>
        </tr>
        <tr v-for="r in pl.expenses" :key="r.accountCode">
          <td>{{ r.accountName }}</td>
          <td class="num">{{ r.amount.toLocaleString() }}</td>
        </tr>
        <tr class="subtotal">
          <td>費用合計</td>
          <td class="num">{{ pl.totalExpense.toLocaleString() }}</td>
        </tr>
        <tr class="total" :class="{ profit: pl.netIncome >= 0, loss: pl.netIncome < 0 }">
          <td>当期純利益</td>
          <td class="num">{{ pl.netIncome.toLocaleString() }}</td>
        </tr>
      </tbody>
    </v-table>
  </div>
</template>

<style scoped>
.pl-table {
  width: 100%;
  max-width: 480px;
}
.num {
  text-align: right;
}
.section th {
  background: #f3f4f6;
}
.subtotal td {
  font-weight: bold;
}
.total td {
  font-weight: bold;
  border-top: 2px solid #374151;
}
.total.profit td {
  color: #16a34a;
}
.total.loss td {
  color: #b91c1c;
}
</style>
