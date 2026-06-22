<script setup lang="ts">
/**
 * 貸借対照表 (M7 F-705)。資産の部と負債・純資産の部を左右に表示する。
 * 資産合計 = 負債合計 + 純資産合計 (当期純利益を含む)。
 */
import { ref, computed, onMounted, watch } from "vue";
import { fetchBalanceSheet, type BalanceSheet } from "@/services/accounting";

const props = defineProps<{ reloadKey: number }>();
const bs = ref<BalanceSheet | null>(null);

const balanced = computed(
  () =>
    bs.value !== null && bs.value.totalAssets === bs.value.totalLiabilities + bs.value.totalEquity,
);

async function load() {
  bs.value = await fetchBalanceSheet();
}

onMounted(load);
watch(() => props.reloadKey, load);
</script>

<template>
  <div v-if="bs" class="bs">
    <div class="columns">
      <v-table density="compact" class="side">
        <thead>
          <tr>
            <th colspan="2">資産の部</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in bs.assets" :key="r.accountCode">
            <td>{{ r.accountName }}</td>
            <td class="num">{{ r.amount.toLocaleString() }}</td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <td>資産合計</td>
            <td class="num">{{ bs.totalAssets.toLocaleString() }}</td>
          </tr>
        </tfoot>
      </v-table>

      <v-table density="compact" class="side">
        <thead>
          <tr>
            <th colspan="2">負債・純資産の部</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in bs.liabilities" :key="r.accountCode">
            <td>{{ r.accountName }}</td>
            <td class="num">{{ r.amount.toLocaleString() }}</td>
          </tr>
          <tr v-for="r in bs.equity" :key="r.accountCode">
            <td>{{ r.accountName }}</td>
            <td class="num">{{ r.amount.toLocaleString() }}</td>
          </tr>
          <tr>
            <td>当期純利益</td>
            <td class="num">{{ bs.netIncome.toLocaleString() }}</td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <td>負債・純資産合計</td>
            <td class="num">{{ (bs.totalLiabilities + bs.totalEquity).toLocaleString() }}</td>
          </tr>
        </tfoot>
      </v-table>
    </div>
    <p class="check" :class="{ ok: balanced }">
      {{ balanced ? "✓ 貸借一致" : "✗ 貸借不一致" }}
    </p>
  </div>
</template>

<style scoped>
.columns {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
}
.side {
  flex: 1;
  min-width: 240px;
}
.num {
  text-align: right;
}
tfoot td {
  font-weight: bold;
  border-top: 2px solid #374151;
}
.check {
  font-weight: bold;
}
.check.ok {
  color: #16a34a;
}
</style>
