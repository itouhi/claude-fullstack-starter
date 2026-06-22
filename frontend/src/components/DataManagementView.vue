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
      <v-text-field
        v-model.number="exportYear"
        label="年度"
        type="number"
        variant="outlined"
        density="compact"
        hide-details
        class="year"
      />
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
      <v-text-field
        v-model.number="carryYear"
        label="繰越元年度"
        type="number"
        variant="outlined"
        density="compact"
        hide-details
        class="year"
      />
      <v-btn color="primary" class="mt-2" @click="loadPreview">繰越内容を確認</v-btn>

      <div v-if="preview" class="preview">
        <p>
          当期純利益 <strong>{{ preview.netIncome.toLocaleString() }}</strong> 円 →
          {{ preview.nextFiscalYear }}年度 期首元入金
          <strong>{{ preview.openingCapitalNext.toLocaleString() }}</strong> 円
        </p>
        <v-table density="compact">
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
        </v-table>
        <v-btn color="primary" class="mt-2" @click="execute">この内容で繰越を実行</v-btn>
      </div>
      <v-alert v-if="message" type="success" density="compact" class="ok mb-2">{{ message }}</v-alert>
      <v-alert v-if="error" type="error" density="compact" class="error mb-2">{{ error }}</v-alert>
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
.num {
  text-align: right;
}
h3 {
  margin-bottom: 0.5rem;
}
</style>
