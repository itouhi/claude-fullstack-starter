<script setup lang="ts">
/**
 * 売上・売掛管理 (M3 F-301/302)。
 *
 * 役務提供売上を発生主義で計上し、取引先別の未入金を表示、入金で消し込む。
 */
import { ref, onMounted } from "vue";
import {
  createSales,
  createReceivablePayment,
  fetchOutstanding,
  type OutstandingRow,
} from "@/services/accounting";

const emit = defineEmits<{ created: [] }>();

// 売上計上フォーム
const counterparty = ref("");
const amount = ref(0);
const saleDate = ref(new Date().toISOString().slice(0, 10));
const description = ref("");
const error = ref("");

const outstanding = ref<OutstandingRow[]>([]);

async function load() {
  outstanding.value = await fetchOutstanding();
}

async function registerSale() {
  error.value = "";
  try {
    await createSales({
      counterparty: counterparty.value,
      amount: amount.value,
      date: saleDate.value,
      description: description.value,
    });
    amount.value = 0;
    description.value = "";
    await load();
    emit("created");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "計上に失敗しました";
  }
}

async function collect(row: OutstandingRow) {
  error.value = "";
  try {
    await createReceivablePayment({
      counterparty: row.counterparty,
      amount: row.balance,
      date: new Date().toISOString().slice(0, 10),
    });
    await load();
    emit("created");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "入金消込に失敗しました";
  }
}

onMounted(load);
</script>

<template>
  <div class="receivables">
    <v-form class="register" @submit.prevent="registerSale">
      <strong>売上を計上 (発生主義)</strong>
      <v-text-field
        v-model="counterparty"
        label="取引先"
        variant="outlined"
        density="compact"
        hide-details
        placeholder="A社"
        required
      />
      <v-text-field
        v-model.number="amount"
        label="金額(税込)"
        variant="outlined"
        density="compact"
        hide-details
        type="number"
        min="1"
        required
      />
      <v-text-field
        v-model="saleDate"
        label="日付"
        variant="outlined"
        density="compact"
        hide-details
        type="date"
        required
      />
      <v-text-field
        v-model="description"
        label="摘要"
        variant="outlined"
        density="compact"
        hide-details
        placeholder="コンサル料 など"
        required
        class="grow"
      />
      <v-btn color="primary" type="submit">売上計上</v-btn>
    </v-form>
    <v-alert v-if="error" type="error" density="compact" class="error mb-2">{{ error }}</v-alert>

    <h3>未入金 (売掛残)</h3>
    <v-table density="compact">
      <thead>
        <tr>
          <th>取引先</th>
          <th class="num">未入金額</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in outstanding" :key="row.counterparty">
          <td>{{ row.counterparty }}</td>
          <td class="num">{{ row.balance.toLocaleString() }}</td>
          <td><v-btn variant="text" size="small" @click="collect(row)">全額入金</v-btn></td>
        </tr>
        <tr v-if="outstanding.length === 0">
          <td colspan="3" class="empty">未入金はありません</td>
        </tr>
      </tbody>
    </v-table>
  </div>
</template>

<style scoped>
.receivables {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.register {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  background: #f9fafb;
  padding: 0.75rem;
  border-radius: 6px;
}
.register .grow {
  flex: 1;
}
.num {
  text-align: right;
}
.empty {
  text-align: center;
  color: #6b7280;
}
.error {
  color: #b91c1c;
}
h3 {
  margin-bottom: 0;
}
</style>
