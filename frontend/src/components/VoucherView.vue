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
    <v-form class="register" @submit.prevent="register">
      <strong>証憑を登録</strong>
      <v-text-field
        v-model="transactionDate"
        type="date"
        label="取引日"
        variant="outlined"
        density="compact"
        hide-details
        required
      />
      <v-text-field
        v-model.number="amount"
        type="number"
        label="金額"
        variant="outlined"
        density="compact"
        hide-details
        min="0"
        required
      />
      <v-text-field
        v-model="counterparty"
        label="取引先"
        variant="outlined"
        density="compact"
        hide-details
        placeholder="ABC商事"
        required
      />
      <v-text-field
        v-model="fileName"
        label="ファイル名"
        variant="outlined"
        density="compact"
        hide-details
        placeholder="receipt.pdf"
      />
      <v-btn type="submit" color="primary">登録</v-btn>
    </v-form>
    <v-alert v-if="error" type="error" density="compact" class="error mb-2">{{ error }}</v-alert>

    <v-form class="search" @submit.prevent="runSearch">
      <strong>検索 (電帳法3キー)</strong>
      <v-text-field
        v-model="search.dateFrom"
        type="date"
        label="取引日 From"
        variant="outlined"
        density="compact"
        hide-details
      />
      <span>〜</span>
      <v-text-field
        v-model="search.dateTo"
        type="date"
        label="取引日 To"
        variant="outlined"
        density="compact"
        hide-details
      />
      <v-text-field
        v-model.number="search.amount"
        type="number"
        label="金額"
        variant="outlined"
        density="compact"
        hide-details
      />
      <v-text-field
        v-model="search.counterparty"
        label="取引先"
        variant="outlined"
        density="compact"
        hide-details
        placeholder="部分一致"
      />
      <v-btn type="submit" color="primary">検索</v-btn>
    </v-form>

    <v-table density="compact" class="results">
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
    </v-table>
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
.num {
  text-align: right;
}
.empty {
  text-align: center;
  color: #6b7280;
}
</style>
