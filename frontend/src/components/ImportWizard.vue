<script setup lang="ts">
/**
 * CSV 明細取込ウィザード (M5 F-503/504)。
 *
 * 銀行/カードの CSV を取り込んで仕訳候補を生成し (相手科目は自動推測)、
 * 候補ごとに相手科目を確認して確定 (仕訳化) またはスキップする。
 */
import { ref, onMounted } from "vue";
import {
  fetchAccounts,
  importCsv,
  fetchImportBatch,
  confirmImportedTransaction,
  skipImportedTransaction,
  type Account,
  type ImportBatch,
} from "@/services/accounting";

const emit = defineEmits<{ created: [] }>();

const accounts = ref<Account[]>([]);
const accountCode = ref("102");
const csvText = ref(
  "日付,摘要,出金金額(円),入金金額(円),残高(円)\n2026-01-15,A社 売上入金,,100000,1100000\n2026-01-20,振込手数料,330,,1099670\n",
);
const batch = ref<ImportBatch | null>(null);
// 明細ごとに選択中の相手科目 (txId -> code)
const counterChoice = ref<Record<number, string>>({});
const error = ref("");

const cashAccounts = () => accounts.value.filter((a) => ["101", "102"].includes(a.code));

async function runImport() {
  error.value = "";
  try {
    batch.value = await importCsv({ accountCode: accountCode.value, csvText: csvText.value });
    counterChoice.value = {};
    for (const tx of batch.value.transactions) {
      counterChoice.value[tx.id] = tx.suggestedAccountCode ?? "";
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "取込に失敗しました";
  }
}

async function confirm(txId: number) {
  error.value = "";
  try {
    await confirmImportedTransaction(batch.value!.id, txId, counterChoice.value[txId] || undefined);
    await refresh();
    emit("created");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "確定に失敗しました";
  }
}

async function skip(txId: number) {
  await skipImportedTransaction(batch.value!.id, txId);
  await refresh();
}

async function refresh() {
  if (!batch.value) return;
  batch.value = await fetchImportBatch(batch.value.id);
}

function nameOf(code: string): string {
  return accounts.value.find((a) => a.code === code)?.name ?? code;
}

onMounted(async () => {
  accounts.value = await fetchAccounts();
});
</script>

<template>
  <div class="import-wizard">
    <div class="setup">
      <label>
        取込先口座:
        <select v-model="accountCode">
          <option v-for="a in cashAccounts()" :key="a.code" :value="a.code">{{ a.name }}</option>
        </select>
      </label>
      <textarea
        v-model="csvText"
        rows="5"
        placeholder="日付,摘要,出金金額(円),入金金額(円),残高(円)"
      ></textarea>
      <button @click="runImport">CSV を取り込む</button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>

    <table v-if="batch" class="candidates">
      <thead>
        <tr>
          <th>日付</th>
          <th>摘要</th>
          <th class="num">入金</th>
          <th class="num">出金</th>
          <th>相手科目 (推測)</th>
          <th>状態</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="tx in batch.transactions" :key="tx.id" :class="tx.status">
          <td>{{ tx.date }}</td>
          <td>{{ tx.description }}</td>
          <td class="num">{{ tx.receipt ? tx.receipt.toLocaleString() : "" }}</td>
          <td class="num">{{ tx.payment ? tx.payment.toLocaleString() : "" }}</td>
          <td>
            <select v-if="tx.status === 'pending'" v-model="counterChoice[tx.id]">
              <option value="">選択</option>
              <option v-for="a in accounts" :key="a.code" :value="a.code">{{ a.name }}</option>
            </select>
            <span v-else>{{ counterChoice[tx.id] ? nameOf(counterChoice[tx.id]) : "—" }}</span>
          </td>
          <td>
            {{
              tx.status === "pending" ? "未処理" : tx.status === "confirmed" ? "確定" : "スキップ"
            }}
          </td>
          <td class="actions">
            <template v-if="tx.status === 'pending'">
              <button class="link" @click="confirm(tx.id)">確定</button>
              <button class="link skip" @click="skip(tx.id)">スキップ</button>
            </template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.import-wizard {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.setup {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background: #f9fafb;
  padding: 0.75rem;
  border-radius: 6px;
}
textarea {
  width: 100%;
  font-family: monospace;
}
.candidates {
  width: 100%;
  border-collapse: collapse;
}
.candidates th,
.candidates td {
  padding: 0.25rem 0.5rem;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
}
.num {
  text-align: right;
}
tr.confirmed {
  color: #16a34a;
}
tr.skipped {
  color: #9ca3af;
}
.actions {
  display: flex;
  gap: 0.5rem;
}
.link {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  padding: 0;
}
.link.skip {
  color: #6b7280;
}
.error {
  color: #b91c1c;
}
</style>
