<script setup lang="ts">
/**
 * 消費税 (簡易課税) 集計 (M8 F-804)。
 *
 * 課税売上を税率別に集計し、みなし仕入率50%で納付税額を表示する。納付額を確定
 * すると仕訳 (借方:租税公課 / 貸方:未払消費税) を計上する。
 */
import { ref, onMounted } from "vue";
import {
  fetchConsumptionTax,
  finalizeConsumptionTax,
  type ConsumptionTax,
} from "@/services/accounting";

const emit = defineEmits<{ created: [] }>();
const fiscalYear = ref(new Date().getFullYear());
const data = ref<ConsumptionTax | null>(null);
const message = ref("");
const error = ref("");

async function load() {
  message.value = "";
  data.value = await fetchConsumptionTax(fiscalYear.value);
}

async function finalize() {
  error.value = "";
  try {
    await finalizeConsumptionTax(fiscalYear.value);
    message.value = "納付確定仕訳を計上しました (借方:租税公課 / 貸方:未払消費税)";
    emit("created");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "確定に失敗しました";
  }
}

onMounted(load);
</script>

<template>
  <div class="tax">
    <v-text-field
      v-model.number="fiscalYear"
      type="number"
      label="会計年度"
      variant="outlined"
      density="compact"
      hide-details
      class="year"
      @change="load"
    />

    <template v-if="data">
      <p class="note">
        事業区分: 第{{ data.businessType }}種 / みなし仕入率 {{ data.deemedPurchaseRate * 100 }}%
      </p>
      <v-table density="compact" class="tax-table">
        <thead>
          <tr>
            <th>税率</th>
            <th class="num">課税売上(税抜)</th>
            <th class="num">消費税額</th>
            <th class="num">控除税額</th>
            <th class="num">納付税額</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in data.taxRates" :key="r.taxCode">
            <td>{{ r.ratePercent }}%</td>
            <td class="num">{{ r.taxableSalesBase.toLocaleString() }}</td>
            <td class="num">{{ r.taxAmount.toLocaleString() }}</td>
            <td class="num">{{ r.deductibleAmount.toLocaleString() }}</td>
            <td class="num">{{ r.payableAmount.toLocaleString() }}</td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <td colspan="2">合計</td>
            <td class="num">{{ data.totalTaxAmount.toLocaleString() }}</td>
            <td class="num">{{ data.totalDeductibleAmount.toLocaleString() }}</td>
            <td class="num highlight">{{ data.totalPayableAmount.toLocaleString() }}</td>
          </tr>
        </tfoot>
      </v-table>
      <v-btn color="primary" :disabled="data.totalPayableAmount <= 0" @click="finalize">
        納付額を確定 (仕訳計上)
      </v-btn>
      <v-alert v-if="message" type="success" density="compact" class="ok mb-2">{{ message }}</v-alert>
      <v-alert v-if="error" type="error" density="compact" class="error mb-2">{{ error }}</v-alert>
    </template>
  </div>
</template>

<style scoped>
.tax {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: flex-start;
}
.year {
  width: 10rem;
}
.note {
  color: #6b7280;
  margin: 0;
}
.tax-table {
  width: 100%;
  max-width: 640px;
}
.num {
  text-align: right;
}
.highlight {
  font-weight: bold;
  color: #2563eb;
}
tfoot td {
  font-weight: bold;
  border-top: 2px solid #374151;
}
</style>
