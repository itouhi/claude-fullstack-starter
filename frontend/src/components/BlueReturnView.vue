<script setup lang="ts">
/**
 * 青色申告決算書プレビュー (M8 F-802)。
 *
 * 損益計算書・貸借対照表・減価償却明細・月別売上を集約して表示する。
 */
import { ref, onMounted, watch } from "vue";
import { fetchBlueReturn, type BlueReturn } from "@/services/accounting";

const props = defineProps<{ reloadKey: number }>();
const fiscalYear = ref(new Date().getFullYear());
const data = ref<BlueReturn | null>(null);

const monthNames = [
  "1月",
  "2月",
  "3月",
  "4月",
  "5月",
  "6月",
  "7月",
  "8月",
  "9月",
  "10月",
  "11月",
  "12月",
];

async function load() {
  data.value = await fetchBlueReturn(fiscalYear.value);
}

onMounted(load);
watch(fiscalYear, load);
watch(() => props.reloadKey, load);
</script>

<template>
  <div class="blue-return">
    <label>
      会計年度:
      <input v-model.number="fiscalYear" type="number" class="year" />
    </label>

    <template v-if="data">
      <section class="summary">
        <div class="card">
          <span class="label">売上 (収益合計)</span>
          <span class="value">{{ data.profitAndLoss.totalRevenue.toLocaleString() }}</span>
        </div>
        <div class="card">
          <span class="label">経費 (費用合計)</span>
          <span class="value">{{ data.profitAndLoss.totalExpense.toLocaleString() }}</span>
        </div>
        <div class="card highlight">
          <span class="label">所得金額 (当期純利益)</span>
          <span class="value">{{ data.profitAndLoss.netIncome.toLocaleString() }}</span>
        </div>
      </section>

      <section>
        <h3>月別売上金額</h3>
        <table class="monthly">
          <thead>
            <tr>
              <th v-for="n in monthNames" :key="n">{{ n }}</th>
              <th class="num">合計</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td v-for="row in data.monthlySales.rows" :key="row.month" class="num">
                {{ row.amount.toLocaleString() }}
              </td>
              <td class="num total">{{ data.monthlySales.total.toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section>
        <h3>減価償却費の計算</h3>
        <table>
          <thead>
            <tr>
              <th>資産名</th>
              <th class="num">取得価額</th>
              <th class="num">耐用年数</th>
              <th class="num">本年分償却費</th>
              <th class="num">期末帳簿価額</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(d, i) in data.depreciation" :key="i">
              <td>{{ d.assetName }}</td>
              <td class="num">{{ d.acquisitionCost.toLocaleString() }}</td>
              <td class="num">{{ d.usefulLifeYears }}</td>
              <td class="num">{{ d.depreciationAmount.toLocaleString() }}</td>
              <td class="num">{{ d.closingBookValue.toLocaleString() }}</td>
            </tr>
            <tr v-if="data.depreciation.length === 0">
              <td colspan="5" class="empty">固定資産がありません</td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </div>
</template>

<style scoped>
.blue-return {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
.year {
  width: 6rem;
}
.summary {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}
.card {
  flex: 1;
  min-width: 160px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.card .label {
  color: #6b7280;
  font-size: 0.85rem;
}
.card .value {
  font-size: 1.4rem;
  font-weight: bold;
}
.card.highlight {
  border-color: #2563eb;
  background: #eff6ff;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  padding: 0.25rem 0.5rem;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
}
.num {
  text-align: right;
}
.monthly th,
.monthly td {
  font-size: 0.8rem;
  padding: 0.25rem;
}
.total {
  font-weight: bold;
}
.empty {
  text-align: center;
  color: #6b7280;
}
h3 {
  margin-bottom: 0.5rem;
}
</style>
