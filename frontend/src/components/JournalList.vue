<script setup lang="ts">
/**
 * 仕訳帳 (M7 F-701)。登録済みの仕訳を時系列で表示する。
 */
import { ref, onMounted, watch } from "vue";
import {
  fetchJournalEntries,
  fetchAccounts,
  type JournalEntry,
  type Account,
} from "@/services/accounting";

const props = defineProps<{ reloadKey: number }>();
const entries = ref<JournalEntry[]>([]);
const accountNames = ref<Record<string, string>>({});

function nameOf(code: string): string {
  return accountNames.value[code] ?? code;
}

async function load() {
  entries.value = await fetchJournalEntries();
}

onMounted(async () => {
  const accounts: Account[] = await fetchAccounts();
  accountNames.value = Object.fromEntries(accounts.map((a) => [a.code, a.name]));
  await load();
});
watch(() => props.reloadKey, load);
</script>

<template>
  <v-table density="compact" class="journal">
    <thead>
      <tr>
        <th>日付</th>
        <th>摘要</th>
        <th>借方科目</th>
        <th>貸方科目</th>
        <th class="num">金額</th>
      </tr>
    </thead>
    <tbody>
      <template v-for="entry in entries" :key="entry.id">
        <tr v-for="(line, i) in entry.lines" :key="`${entry.id}-${i}`">
          <td>{{ i === 0 ? entry.date : "" }}</td>
          <td>{{ i === 0 ? entry.description : "" }}</td>
          <td>{{ line.side === "debit" ? nameOf(line.accountCode) : "" }}</td>
          <td>{{ line.side === "credit" ? nameOf(line.accountCode) : "" }}</td>
          <td class="num">{{ line.amount.toLocaleString() }}</td>
        </tr>
      </template>
      <tr v-if="entries.length === 0">
        <td colspan="5" class="empty">仕訳がありません</td>
      </tr>
    </tbody>
  </v-table>
</template>

<style scoped>
.journal {
  width: 100%;
}
.num {
  text-align: right;
}
.empty {
  text-align: center;
  color: #6b7280;
}
</style>
