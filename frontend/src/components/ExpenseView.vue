<script setup lang="ts">
/**
 * 経費・支払管理 (M4 F-401/403)。
 *
 * 経費を科目別に計上 (即時払い/未払) し、取引先別の未払金を表示、支払で消し込む。
 */
import { ref, computed, onMounted } from "vue";
import {
  fetchAccounts,
  createExpense,
  payPayable,
  fetchPayables,
  type Account,
  type PayableRow,
} from "@/services/accounting";

const emit = defineEmits<{ created: [] }>();

const accounts = ref<Account[]>([]);
const expenseAccounts = computed(() => accounts.value.filter((a) => a.type === "expense"));

// 入力フォーム
const expenseAccountCode = ref("");
const amount = ref(0);
const creditAccountCode = ref("101");
const description = ref("");
const expenseDate = ref(new Date().toISOString().slice(0, 10));
const counterparty = ref("");
const error = ref("");

const payables = ref<PayableRow[]>([]);
const isPayable = computed(() => creditAccountCode.value === "305");

async function load() {
  payables.value = await fetchPayables();
}

async function register() {
  error.value = "";
  try {
    await createExpense({
      expenseAccountCode: expenseAccountCode.value,
      amount: amount.value,
      creditAccountCode: creditAccountCode.value,
      description: description.value,
      date: expenseDate.value,
      counterparty: isPayable.value ? counterparty.value : null,
    });
    amount.value = 0;
    description.value = "";
    counterparty.value = "";
    await load();
    emit("created");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "計上に失敗しました";
  }
}

async function pay(row: PayableRow) {
  error.value = "";
  try {
    await payPayable({
      counterparty: row.counterparty,
      amount: row.balance,
      date: new Date().toISOString().slice(0, 10),
    });
    await load();
    emit("created");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "支払消込に失敗しました";
  }
}

onMounted(async () => {
  accounts.value = await fetchAccounts();
  await load();
});
</script>

<template>
  <div class="expenses">
    <form class="register" @submit.prevent="register">
      <strong>経費を計上</strong>
      <label>
        勘定科目
        <select v-model="expenseAccountCode" required>
          <option value="" disabled>選択</option>
          <option v-for="a in expenseAccounts" :key="a.code" :value="a.code">{{ a.name }}</option>
        </select>
      </label>
      <label>金額(税込) <input v-model.number="amount" type="number" min="1" required /></label>
      <label>
        支払方法
        <select v-model="creditAccountCode">
          <option value="101">現金</option>
          <option value="102">普通預金</option>
          <option value="305">未払 (後払い)</option>
        </select>
      </label>
      <label v-if="isPayable">取引先 <input v-model="counterparty" placeholder="C社" /></label>
      <label>日付 <input v-model="expenseDate" type="date" required /></label>
      <label class="grow"
        >摘要 <input v-model="description" placeholder="通信費 など" required
      /></label>
      <button type="submit">経費計上</button>
    </form>
    <p v-if="error" class="error">{{ error }}</p>

    <h3>未払金</h3>
    <table>
      <thead>
        <tr>
          <th>取引先</th>
          <th class="num">未払額</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in payables" :key="row.counterparty">
          <td>{{ row.counterparty }}</td>
          <td class="num">{{ row.balance.toLocaleString() }}</td>
          <td><button class="link" @click="pay(row)">全額支払</button></td>
        </tr>
        <tr v-if="payables.length === 0">
          <td colspan="3" class="empty">未払金はありません</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.expenses {
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
