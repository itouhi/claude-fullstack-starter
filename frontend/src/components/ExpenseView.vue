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
    <v-form class="register" @submit.prevent="register">
      <strong>経費を計上</strong>
      <v-select
        v-model="expenseAccountCode"
        label="勘定科目"
        variant="outlined"
        density="compact"
        hide-details
        :items="expenseAccounts"
        item-title="name"
        item-value="code"
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
      <v-select
        v-model="creditAccountCode"
        label="支払方法"
        variant="outlined"
        density="compact"
        hide-details
        :items="[{title:'現金',value:'101'},{title:'普通預金',value:'102'},{title:'未払 (後払い)',value:'305'}]"
      />
      <v-text-field
        v-if="isPayable"
        v-model="counterparty"
        label="取引先"
        variant="outlined"
        density="compact"
        hide-details
        placeholder="C社"
      />
      <v-text-field
        v-model="expenseDate"
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
        placeholder="通信費 など"
        required
        class="grow"
      />
      <v-btn color="primary" type="submit">経費計上</v-btn>
    </v-form>
    <v-alert v-if="error" type="error" density="compact" class="error mb-2">{{ error }}</v-alert>

    <h3>未払金</h3>
    <v-table density="compact">
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
          <td><v-btn variant="text" size="small" @click="pay(row)">全額支払</v-btn></td>
        </tr>
        <tr v-if="payables.length === 0">
          <td colspan="3" class="empty">未払金はありません</td>
        </tr>
      </tbody>
    </v-table>
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
