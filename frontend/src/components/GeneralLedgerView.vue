<script setup lang="ts">
/**
 * 総勘定元帳 (M7 F-702)。科目を選び、相手科目・借貸・繰越残高を時系列で表示する。
 */
import { ref, onMounted, watch } from "vue";
import {
  fetchAccounts,
  fetchGeneralLedger,
  type Account,
  type GeneralLedger,
} from "@/services/accounting";

const props = defineProps<{ reloadKey: number }>();
const accounts = ref<Account[]>([]);
const accountCode = ref("101");
const ledger = ref<GeneralLedger | null>(null);

async function load() {
  ledger.value = await fetchGeneralLedger(accountCode.value);
}

onMounted(async () => {
  accounts.value = await fetchAccounts();
  await load();
});
watch(accountCode, load);
watch(() => props.reloadKey, load);
</script>

<template>
  <div class="ledger">
    <v-select
      v-model="accountCode"
      label="勘定科目"
      variant="outlined"
      density="compact"
      hide-details
      :items="accounts"
      item-title="name"
      item-value="code"
    />

    <v-table v-if="ledger" density="compact" class="gl">
      <thead>
        <tr>
          <th>日付</th>
          <th>摘要</th>
          <th>相手科目</th>
          <th class="num">借方</th>
          <th class="num">貸方</th>
          <th class="num">残高</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, i) in ledger.rows" :key="i">
          <td>{{ row.date }}</td>
          <td>{{ row.description }}</td>
          <td>{{ row.counterAccount }}</td>
          <td class="num">{{ row.debitAmount ? row.debitAmount.toLocaleString() : "" }}</td>
          <td class="num">{{ row.creditAmount ? row.creditAmount.toLocaleString() : "" }}</td>
          <td class="num">{{ row.runningBalance.toLocaleString() }}</td>
        </tr>
        <tr v-if="ledger.rows.length === 0">
          <td colspan="6" class="empty">取引がありません</td>
        </tr>
      </tbody>
      <tfoot>
        <tr>
          <td colspan="5">期末残高</td>
          <td class="num">{{ ledger.closingBalance.toLocaleString() }}</td>
        </tr>
      </tfoot>
    </v-table>
  </div>
</template>

<style scoped>
.ledger {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
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
</style>
