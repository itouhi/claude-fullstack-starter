<script setup lang="ts">
/**
 * 出納帳 (M5 F-501/F-502/F-102)。
 *
 * 口座 (現金・預金) を選び、入金/出金の簡易入力で記帳する。借方/貸方を意識せず
 * 入力でき、裏で複式仕訳に変換される (N-9)。出納帳は仕訳の読み取りビュー。
 */
import { ref, computed, onMounted, watch } from "vue";
import {
  fetchAccounts,
  fetchCashBook,
  createCashEntry,
  type Account,
  type CashBook,
} from "@/services/accounting";

const props = defineProps<{ reloadKey: number }>();
const emit = defineEmits<{ created: [] }>();

const accounts = ref<Account[]>([]);
const accountCode = ref("101");
const book = ref<CashBook | null>(null);

// 簡易入力フォーム
const direction = ref<"receipt" | "payment">("payment");
const counterCode = ref("");
const amount = ref(0);
const description = ref("");
const entryDate = ref(new Date().toISOString().slice(0, 10));
const error = ref("");
const submitting = ref(false);

// 口座候補 = 資産科目 (現金・預金)。相手科目候補 = それ以外。
const cashAccounts = computed(() => accounts.value.filter((a) => ["101", "102"].includes(a.code)));
const counterAccounts = computed(() => accounts.value.filter((a) => a.type !== "asset"));

async function loadBook() {
  book.value = await fetchCashBook(accountCode.value);
}

async function submit() {
  error.value = "";
  submitting.value = true;
  try {
    await createCashEntry({
      accountCode: accountCode.value,
      direction: direction.value,
      counterCode: counterCode.value,
      amount: amount.value,
      description: description.value,
      date: entryDate.value,
    });
    description.value = "";
    amount.value = 0;
    counterCode.value = "";
    await loadBook();
    emit("created");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "登録に失敗しました";
  } finally {
    submitting.value = false;
  }
}

onMounted(async () => {
  accounts.value = await fetchAccounts();
  await loadBook();
});
watch(accountCode, loadBook);
watch(() => props.reloadKey, loadBook);
</script>

<template>
  <div class="cash-book">
    <label class="account-select">
      口座:
      <select v-model="accountCode">
        <option v-for="a in cashAccounts" :key="a.code" :value="a.code">{{ a.name }}</option>
      </select>
    </label>

    <form class="quick-entry" @submit.prevent="submit">
      <select v-model="direction">
        <option value="receipt">入金</option>
        <option value="payment">出金</option>
      </select>
      <select v-model="counterCode" required>
        <option value="" disabled>相手科目</option>
        <option v-for="a in counterAccounts" :key="a.code" :value="a.code">{{ a.name }}</option>
      </select>
      <input v-model.number="amount" type="number" min="1" placeholder="金額" required />
      <input v-model="description" placeholder="摘要" required />
      <input v-model="entryDate" type="date" required />
      <button type="submit" :disabled="submitting">記帳</button>
    </form>
    <p v-if="error" class="error">{{ error }}</p>

    <table v-if="book" class="book">
      <thead>
        <tr>
          <th>日付</th>
          <th>摘要</th>
          <th>相手科目</th>
          <th class="num">入金</th>
          <th class="num">出金</th>
          <th class="num">残高</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, i) in book.rows" :key="i">
          <td>{{ row.date }}</td>
          <td>{{ row.description }}</td>
          <td>{{ row.counterAccount }}</td>
          <td class="num">{{ row.receipt ? row.receipt.toLocaleString() : "" }}</td>
          <td class="num">{{ row.payment ? row.payment.toLocaleString() : "" }}</td>
          <td class="num">{{ row.balance.toLocaleString() }}</td>
        </tr>
        <tr v-if="book.rows.length === 0">
          <td colspan="6" class="empty">取引がありません</td>
        </tr>
      </tbody>
      <tfoot>
        <tr>
          <td colspan="5">残高</td>
          <td class="num">{{ book.closingBalance.toLocaleString() }}</td>
        </tr>
      </tfoot>
    </table>
  </div>
</template>

<style scoped>
.cash-book {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.quick-entry {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  background: #f9fafb;
  padding: 0.75rem;
  border-radius: 6px;
}
.book {
  width: 100%;
  border-collapse: collapse;
}
.book th,
.book td {
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
tfoot td {
  font-weight: bold;
}
.error {
  color: #b91c1c;
}
</style>
