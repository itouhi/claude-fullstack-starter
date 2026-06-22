<script setup lang="ts">
/**
 * 仕訳入力フォーム (M2 F-101)。
 *
 * 複数明細を借方・貸方で入力し、借貸の一致をその場で確認したうえで登録する。
 * 登録成功時に `created` を emit する。
 */
import { ref, computed, onMounted } from "vue";
import {
  fetchAccounts,
  fetchTaxCategories,
  createJournalEntry,
  type Account,
  type TaxCategory,
  type JournalLine,
} from "@/services/accounting";

const emit = defineEmits<{ created: [] }>();

const accounts = ref<Account[]>([]);
const taxCategories = ref<TaxCategory[]>([]);
const entryDate = ref(new Date().toISOString().slice(0, 10));
const description = ref("");
const lines = ref<JournalLine[]>([
  { side: "debit", accountCode: "", amount: 0, taxCode: "" },
  { side: "credit", accountCode: "", amount: 0, taxCode: "" },
]);
const error = ref("");
const submitting = ref(false);

const debitTotal = computed(() =>
  lines.value.filter((l) => l.side === "debit").reduce((s, l) => s + (l.amount || 0), 0),
);
const creditTotal = computed(() =>
  lines.value.filter((l) => l.side === "credit").reduce((s, l) => s + (l.amount || 0), 0),
);
const balanced = computed(() => debitTotal.value === creditTotal.value && debitTotal.value > 0);

function addLine(side: "debit" | "credit") {
  lines.value.push({ side, accountCode: "", amount: 0, taxCode: "" });
}

function removeLine(index: number) {
  lines.value.splice(index, 1);
}

function onAccountChange(line: JournalLine) {
  const account = accounts.value.find((a) => a.code === line.accountCode);
  if (account?.defaultTaxCode) line.taxCode = account.defaultTaxCode;
}

async function submit() {
  error.value = "";
  submitting.value = true;
  try {
    await createJournalEntry({
      date: entryDate.value,
      description: description.value,
      lines: lines.value.map((l) => ({
        side: l.side,
        accountCode: l.accountCode,
        amount: l.amount,
        taxCode: l.taxCode || null,
      })),
    });
    description.value = "";
    lines.value = [
      { side: "debit", accountCode: "", amount: 0, taxCode: "" },
      { side: "credit", accountCode: "", amount: 0, taxCode: "" },
    ];
    emit("created");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "登録に失敗しました";
  } finally {
    submitting.value = false;
  }
}

onMounted(async () => {
  accounts.value = await fetchAccounts();
  taxCategories.value = await fetchTaxCategories();
});
</script>

<template>
  <form class="entry-form" @submit.prevent="submit">
    <div class="header">
      <label>日付 <input v-model="entryDate" type="date" required /></label>
      <label class="grow"
        >摘要 <input v-model="description" placeholder="役務提供売上 など" required
      /></label>
    </div>

    <table class="lines">
      <thead>
        <tr>
          <th>貸借</th>
          <th>勘定科目</th>
          <th>金額 (円)</th>
          <th>税区分</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(line, i) in lines" :key="i" :class="line.side">
          <td>
            <select v-model="line.side">
              <option value="debit">借方</option>
              <option value="credit">貸方</option>
            </select>
          </td>
          <td>
            <select v-model="line.accountCode" required @change="onAccountChange(line)">
              <option value="" disabled>選択</option>
              <option v-for="a in accounts" :key="a.code" :value="a.code">{{ a.name }}</option>
            </select>
          </td>
          <td><input v-model.number="line.amount" type="number" min="1" required /></td>
          <td>
            <select v-model="line.taxCode">
              <option value="">—</option>
              <option v-for="t in taxCategories" :key="t.code" :value="t.code">{{ t.name }}</option>
            </select>
          </td>
          <td><button type="button" class="link" @click="removeLine(i)">削除</button></td>
        </tr>
      </tbody>
    </table>

    <div class="actions">
      <button type="button" class="link" @click="addLine('debit')">+ 借方</button>
      <button type="button" class="link" @click="addLine('credit')">+ 貸方</button>
    </div>

    <div class="totals" :class="{ ok: balanced, ng: !balanced }">
      借方 {{ debitTotal.toLocaleString() }} / 貸方 {{ creditTotal.toLocaleString() }}
      <span v-if="balanced">✓ 一致</span>
      <span v-else>✗ 不一致</span>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <button type="submit" :disabled="!balanced || submitting">仕訳を登録</button>
  </form>
</template>

<style scoped>
.entry-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.header {
  display: flex;
  gap: 1rem;
}
.header .grow {
  flex: 1;
}
.header input {
  width: 100%;
}
.lines {
  width: 100%;
  border-collapse: collapse;
}
.lines th,
.lines td {
  padding: 0.25rem 0.5rem;
  text-align: left;
}
.lines tr.debit td:first-child {
  border-left: 3px solid #2563eb;
}
.lines tr.credit td:first-child {
  border-left: 3px solid #dc2626;
}
.lines input,
.lines select {
  width: 100%;
}
.actions {
  display: flex;
  gap: 1rem;
}
.totals.ok {
  color: #16a34a;
}
.totals.ng {
  color: #b91c1c;
}
.error {
  color: #b91c1c;
}
.link {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  padding: 0;
}
</style>
