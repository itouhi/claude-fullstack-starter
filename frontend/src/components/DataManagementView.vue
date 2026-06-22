<script setup lang="ts">
/**
 * データ管理 (M9)。帳簿・決算書の CSV エクスポート (F-902) と年度繰越 (F-904)。
 */
import { ref } from "vue";
import {
  exportUrl,
  fetchCarryForwardPreview,
  executeCarryForward,
  type YearEndPreview,
} from "@/services/accounting";

const emit = defineEmits<{ created: [] }>();

const exportYear = ref(new Date().getFullYear());
const reports = [
  { key: "journal", label: "仕訳帳" },
  { key: "trial-balance", label: "試算表" },
  { key: "pl", label: "損益計算書" },
  { key: "bs", label: "貸借対照表" },
];

const carryYear = ref(new Date().getFullYear() - 1);
const preview = ref<YearEndPreview | null>(null);
const message = ref("");
const error = ref("");

async function loadPreview() {
  message.value = "";
  error.value = "";
  preview.value = await fetchCarryForwardPreview(carryYear.value);
}

async function execute() {
  error.value = "";
  try {
    await executeCarryForward(carryYear.value);
    message.value = `${carryYear.value}年度を繰越し、${carryYear.value + 1}年度の期首振替仕訳を計上しました`;
    preview.value = null;
    emit("created");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "繰越に失敗しました";
  }
}
</script>

<template>
  <div class="data-mgmt">
    <section>
      <h3>CSVエクスポート (税理士共有)</h3>
      <label>年度: <input v-model.number="exportYear" type="number" class="year" /></label>
      <div class="links">
        <a
          v-for="r in reports"
          :key="r.key"
          :href="exportUrl(r.key, exportYear)"
          download
          class="export-link"
          >{{ r.label }} CSV</a
        >
      </div>
    </section>

    <section>
      <h3>年度繰越</h3>
      <label>繰越元年度: <input v-model.number="carryYear" type="number" class="year" /></label>
      <button @click="loadPreview">繰越内容を確認</button>

      <div v-if="preview" class="preview">
        <p>
          当期純利益 <strong>{{ preview.netIncome.toLocaleString() }}</strong> 円 →
          {{ preview.nextFiscalYear }}年度 期首元入金
          <strong>{{ preview.openingCapitalNext.toLocaleString() }}</strong> 円
        </p>
        <table>
          <thead>
            <tr>
              <th>繰越科目</th>
              <th class="num">期末残高</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in preview.balanceForward" :key="b.accountCode">
              <td>{{ b.accountName }}</td>
              <td class="num">{{ b.closingBalance.toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>
        <button class="primary" @click="execute">この内容で繰越を実行</button>
      </div>
      <p v-if="message" class="ok">{{ message }}</p>
      <p v-if="error" class="error">{{ error }}</p>
    </section>
  </div>
</template>

<style scoped>
.data-mgmt {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}
.year {
  width: 6rem;
}
.links {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
}
.export-link {
  color: #2563eb;
}
.preview {
  margin-top: 0.75rem;
}
table {
  border-collapse: collapse;
  min-width: 320px;
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
.primary {
  margin-top: 0.5rem;
}
.ok {
  color: #16a34a;
}
.error {
  color: #b91c1c;
}
h3 {
  margin-bottom: 0.5rem;
}
</style>
