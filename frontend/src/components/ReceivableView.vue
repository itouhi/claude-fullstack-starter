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
    <form class="register" @submit.prevent="registerSale">
      <strong>売上を計上 (発生主義)</strong>
      <label>取引先 <input v-model="counterparty" placeholder="A社" required /></label>
      <label>金額(税込) <input v-model.number="amount" type="number" min="1" required /></label>
      <label>日付 <input v-model="saleDate" type="date" required /></label>
      <label class="grow"
        >摘要 <input v-model="description" placeholder="コンサル料 など" required
      /></label>
      <button type="submit">売上計上</button>
    </form>
    <p v-if="error" class="error">{{ error }}</p>

    <h3>未入金 (売掛残)</h3>
    <table>
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
          <td><button class="link" @click="collect(row)">全額入金</button></td>
        </tr>
        <tr v-if="outstanding.length === 0">
          <td colspan="3" class="empty">未入金はありません</td>
        </tr>
      </tbody>
    </table>
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
table {
  width: 100%;
  max-width: 520px;
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
.empty {
  text-align: center;
  color: #6b7280;
}
.link {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  padding: 0;
}
.error {
  color: #b91c1c;
}
h3 {
  margin-bottom: 0;
}
</style>
