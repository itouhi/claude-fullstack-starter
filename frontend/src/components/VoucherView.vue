<script setup lang="ts">
/**
 * 証憑保存・検索 (X3 F-402 — 電子帳簿保存法対応)。
 *
 * 証憑を登録し、電帳法の3キー (取引日・金額・取引先) で検索する。
 */
import { ref, onMounted } from "vue";
import {
  createVoucher,
  searchVouchers,
  type Voucher,
  type VoucherSearch,
} from "@/services/accounting";

// 登録フォーム
const transactionDate = ref(new Date().toISOString().slice(0, 10));
const amount = ref(0);
const counterparty = ref("");
const fileName = ref("");
const error = ref("");

// 検索条件
const search = ref<VoucherSearch>({});
const results = ref<Voucher[]>([]);

async function register() {
  error.value = "";
  try {
    await createVoucher({
      transactionDate: transactionDate.value,
      amount: amount.value,
      counterparty: counterparty.value,
      fileName: fileName.value || "voucher.pdf",
    });
    amount.value = 0;
    counterparty.value = "";
    fileName.value = "";
    await runSearch();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "登録に失敗しました";
  }
}

async function runSearch() {
  results.value = await searchVouchers(search.value);
}

onMounted(runSearch);
</script>

<template>
  <div class="vouchers">
    <form class="register" @submit.prevent="register">
      <strong>証憑を登録</strong>
      <label>取引日 <input v-model="transactionDate" type="date" required /></label>
      <label>金額 <input v-model.number="amount" type="number" min="0" required /></label>
      <label>取引先 <input v-model="counterparty" placeholder="ABC商事" required /></label>
      <label>ファイル名 <input v-model="fileName" placeholder="receipt.pdf" /></label>
      <button type="submit">登録</button>
    </form>
    <p v-if="error" class="error">{{ error }}</p>

    <form class="search" @submit.prevent="runSearch">
      <strong>検索 (電帳法3キー)</strong>
      <label
        >取引日 <input v-model="search.dateFrom" type="date" /> 〜
        <input v-model="search.dateTo" type="date"
      /></label>
      <label>金額 <input v-model.number="search.amount" type="number" /></label>
      <label>取引先 <input v-model="search.counterparty" placeholder="部分一致" /></label>
      <button type="submit">検索</button>
    </form>

    <table class="results">
      <thead>
        <tr>
          <th>取引日</th>
          <th class="num">金額</th>
          <th>取引先</th>
          <th>ファイル</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="v in results" :key="v.id">
          <td>{{ v.transactionDate }}</td>
          <td class="num">{{ v.amount.toLocaleString() }}</td>
          <td>{{ v.counterparty }}</td>
          <td>{{ v.fileName }}</td>
        </tr>
        <tr v-if="results.length === 0">
          <td colspan="4" class="empty">証憑がありません</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.vouchers {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.register,
.search {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  background: #f9fafb;
  padding: 0.75rem;
  border-radius: 6px;
}
.results {
  width: 100%;
  border-collapse: collapse;
}
.results th,
.results td {
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
.error {
  color: #b91c1c;
}
</style>
