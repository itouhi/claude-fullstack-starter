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
  <v-form class="entry-form" @submit.prevent="submit">
    <div class="header">
      <v-text-field
        v-model="entryDate"
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
        placeholder="役務提供売上 など"
        required
        class="grow"
      />
    </div>

    <v-table class="lines">
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
            <v-select
              v-model="line.side"
              :items="[{ title: '借方', value: 'debit' }, { title: '貸方', value: 'credit' }]"
              variant="outlined"
              density="compact"
              hide-details
            />
          </td>
          <td>
            <v-select
              v-model="line.accountCode"
              :items="accounts"
              item-title="name"
              item-value="code"
              variant="outlined"
              density="compact"
              hide-details
              required
              @update:model-value="onAccountChange(line)"
            />
          </td>
          <td>
            <v-text-field
              v-model.number="line.amount"
              type="number"
              min="1"
              variant="outlined"
              density="compact"
              hide-details
              required
            />
          </td>
          <td>
            <v-select
              v-model="line.taxCode"
              :items="[{ title: '—', value: '' }, ...taxCategories.map(t => ({ title: t.name, value: t.code }))]"
              variant="outlined"
              density="compact"
              hide-details
            />
          </td>
          <td>
            <v-btn variant="text" size="small" color="primary" type="button" @click="removeLine(i)">削除</v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>

    <div class="actions">
      <v-btn variant="text" size="small" color="primary" type="button" @click="addLine('debit')">+ 借方</v-btn>
      <v-btn variant="text" size="small" color="primary" type="button" @click="addLine('credit')">+ 貸方</v-btn>
    </div>

    <div class="totals" :class="{ ok: balanced, ng: !balanced }">
      借方 {{ debitTotal.toLocaleString() }} / 貸方 {{ creditTotal.toLocaleString() }}
      <span v-if="balanced">✓ 一致</span>
      <span v-else>✗ 不一致</span>
    </div>

    <v-alert v-if="error" type="error" density="compact" class="error mb-2">{{ error }}</v-alert>
    <v-btn color="primary" type="submit" :disabled="!balanced || submitting">仕訳を登録</v-btn>
  </v-form>
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
</style>
