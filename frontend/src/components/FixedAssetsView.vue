<script setup lang="ts">
/**
 * 固定資産台帳 (M6 F-601/602/603)。
 *
 * 固定資産を登録し、償却予定表の確認と当期減価償却の仕訳計上を行う。
 * 30万円未満では少額特例の選択肢を表示する (F-603)。
 */
import { ref, computed, onMounted } from "vue";
import {
  fetchFixedAssets,
  createFixedAsset,
  fetchDepreciationSchedule,
  postDepreciation,
  type FixedAsset,
  type DepreciationEntry,
} from "@/services/accounting";

const emit = defineEmits<{ created: [] }>();

const assets = ref<FixedAsset[]>([]);
const error = ref("");

// 登録フォーム
const name = ref("");
const acquisitionDate = ref(new Date().toISOString().slice(0, 10));
const acquisitionCost = ref(0);
const usefulLifeYears = ref(5);
const businessUseRatio = ref(100);
const useSmallAmountSpecial = ref(false);

const eligibleForSpecial = computed(
  () => acquisitionCost.value > 0 && acquisitionCost.value < 300000,
);

// 償却予定表
const selectedAssetId = ref<number | null>(null);
const schedule = ref<DepreciationEntry[]>([]);
const depreciationYear = ref(new Date().getFullYear());

const statusLabels: Record<string, string> = {
  active: "償却中",
  fully_depreciated: "償却済",
  deleted: "削除",
};

async function loadAssets() {
  assets.value = await fetchFixedAssets();
}

async function register() {
  error.value = "";
  try {
    await createFixedAsset({
      name: name.value,
      acquisitionDate: acquisitionDate.value,
      acquisitionCost: acquisitionCost.value,
      usefulLifeYears: usefulLifeYears.value,
      businessUseRatio: businessUseRatio.value / 100,
      useSmallAmountSpecial: eligibleForSpecial.value && useSmallAmountSpecial.value,
    });
    name.value = "";
    acquisitionCost.value = 0;
    useSmallAmountSpecial.value = false;
    await loadAssets();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "登録に失敗しました";
  }
}

async function showSchedule(asset: FixedAsset) {
  selectedAssetId.value = asset.id;
  schedule.value = await fetchDepreciationSchedule(asset.id);
}

async function depreciate(asset: FixedAsset) {
  error.value = "";
  try {
    await postDepreciation(asset.id, depreciationYear.value);
    await loadAssets();
    if (selectedAssetId.value === asset.id) await showSchedule(asset);
    emit("created");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "償却計上に失敗しました";
  }
}

onMounted(loadAssets);
</script>

<template>
  <div class="fixed-assets">
    <form class="register" @submit.prevent="register">
      <input v-model="name" placeholder="資産名 (例: ノートPC)" required />
      <label>取得日 <input v-model="acquisitionDate" type="date" required /></label>
      <label
        >取得価額 <input v-model.number="acquisitionCost" type="number" min="1" required
      /></label>
      <label
        >耐用年数 <input v-model.number="usefulLifeYears" type="number" min="1" required
      /></label>
      <label
        >事業割合% <input v-model.number="businessUseRatio" type="number" min="1" max="100"
      /></label>
      <label v-if="eligibleForSpecial" class="special">
        <input v-model="useSmallAmountSpecial" type="checkbox" /> 少額特例 (即時償却)
      </label>
      <button type="submit">資産を登録</button>
    </form>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="depreciate-bar">
      減価償却を計上する年度:
      <input v-model.number="depreciationYear" type="number" class="year" />
    </div>

    <table class="assets">
      <thead>
        <tr>
          <th>資産名</th>
          <th>取得日</th>
          <th class="num">取得価額</th>
          <th class="num">未償却残高</th>
          <th>状態</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="a in assets" :key="a.id">
          <td>{{ a.name }}{{ a.isSmallAmountSpecial ? " (少額特例)" : "" }}</td>
          <td>{{ a.acquisitionDate }}</td>
          <td class="num">{{ a.acquisitionCost.toLocaleString() }}</td>
          <td class="num">{{ a.bookValue.toLocaleString() }}</td>
          <td>{{ statusLabels[a.status] }}</td>
          <td class="actions">
            <button class="link" @click="showSchedule(a)">予定表</button>
            <button class="link" @click="depreciate(a)">当期償却を計上</button>
          </td>
        </tr>
        <tr v-if="assets.length === 0">
          <td colspan="6" class="empty">固定資産がありません</td>
        </tr>
      </tbody>
    </table>

    <div v-if="selectedAssetId !== null" class="schedule">
      <h3>償却予定表</h3>
      <table>
        <thead>
          <tr>
            <th>年度</th>
            <th class="num">期首残高</th>
            <th class="num">当期償却費</th>
            <th class="num">うち事業分</th>
            <th class="num">うち家事分</th>
            <th class="num">期末残高</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in schedule" :key="row.fiscalYear">
            <td>{{ row.fiscalYear }}</td>
            <td class="num">{{ row.openingBookValue.toLocaleString() }}</td>
            <td class="num">{{ row.depreciationAmount.toLocaleString() }}</td>
            <td class="num">{{ row.businessDepreciation.toLocaleString() }}</td>
            <td class="num">{{ row.privateDepreciation.toLocaleString() }}</td>
            <td class="num">{{ row.closingBookValue.toLocaleString() }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.fixed-assets {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.register {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  background: #f9fafb;
  padding: 0.75rem;
  border-radius: 6px;
}
.register input[type="number"] {
  width: 7rem;
}
.special {
  color: #b45309;
}
.depreciate-bar .year {
  width: 6rem;
}
table {
  width: 100%;
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
.actions {
  display: flex;
  gap: 0.5rem;
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
</style>
