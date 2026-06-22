<script setup lang="ts">
/**
 * 合計残高試算表 (M7 F-703)。勘定科目別の借方・貸方合計と残高を表示する。
 */
import { ref, onMounted, watch } from "vue";
import { fetchTrialBalance, type TrialBalance } from "@/services/accounting";

const props = defineProps<{ reloadKey: number }>();
const tb = ref<TrialBalance | null>(null);

const typeLabels: Record<string, string> = {
  asset: "資産",
  liability: "負債",
  equity: "純資産",
  revenue: "収益",
  expense: "費用",
};

async function load() {
  tb.value = await fetchTrialBalance();
}

onMounted(load);
watch(() => props.reloadKey, load);
</script>

<template>
  <div v-if="tb">
    <table class="tb">
      <thead>
        <tr>
          <th>区分</th>
          <th>勘定科目</th>
          <th class="num">借方合計</th>
          <th class="num">貸方合計</th>
          <th class="num">残高</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in tb.rows" :key="row.accountCode">
          <td>{{ typeLabels[row.type] }}</td>
          <td>{{ row.accountName }}</td>
          <td class="num">{{ row.debitTotal.toLocaleString() }}</td>
          <td class="num">{{ row.creditTotal.toLocaleString() }}</td>
          <td class="num">{{ row.balance.toLocaleString() }}</td>
        </tr>
        <tr v-if="tb.rows.length === 0">
          <td colspan="5" class="empty">データがありません</td>
        </tr>
      </tbody>
      <tfoot>
        <tr :class="{ ok: tb.debitTotal === tb.creditTotal }">
          <td colspan="2">合計</td>
          <td class="num">{{ tb.debitTotal.toLocaleString() }}</td>
          <td class="num">{{ tb.creditTotal.toLocaleString() }}</td>
          <td class="num">{{ tb.debitTotal === tb.creditTotal ? "✓ 貸借一致" : "✗ 不一致" }}</td>
        </tr>
      </tfoot>
    </table>
  </div>
</template>

<style scoped>
.tb {
  width: 100%;
  border-collapse: collapse;
}
.tb th,
.tb td {
  padding: 0.25rem 0.5rem;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
}
.num {
  text-align: right;
}
.empty {
  text-align: center;
  color: #6b7280;
}
tfoot .ok {
  color: #16a34a;
  font-weight: bold;
}
</style>
