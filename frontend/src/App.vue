<script setup lang="ts">
/**
 * 会計システムのシェル (Vuetify 3)。
 *
 * 左サイドのナビゲーションドロワーで機能を選び、選択した画面のみを `<component :is>`
 * で都度マウントする (呼び出し時にタグ配置 = 遅延レンダリング)。
 *
 * 由来: 全体基本設計 §1.1 (SPA + BFF) / UI モダン化 (Vuetify)。
 */
import { computed, ref, shallowRef } from "vue";
import JournalEntryForm from "@/components/JournalEntryForm.vue";
import JournalList from "@/components/JournalList.vue";
import CashBook from "@/components/CashBook.vue";
import GeneralLedgerView from "@/components/GeneralLedgerView.vue";
import TrialBalanceView from "@/components/TrialBalanceView.vue";
import ProfitAndLossView from "@/components/ProfitAndLossView.vue";
import BalanceSheetView from "@/components/BalanceSheetView.vue";
import FixedAssetsView from "@/components/FixedAssetsView.vue";
import BlueReturnView from "@/components/BlueReturnView.vue";
import DashboardView from "@/components/DashboardView.vue";
import ImportWizard from "@/components/ImportWizard.vue";
import TaxView from "@/components/TaxView.vue";
import VoucherView from "@/components/VoucherView.vue";
import ReceivableView from "@/components/ReceivableView.vue";
import ExpenseView from "@/components/ExpenseView.vue";
import DataManagementView from "@/components/DataManagementView.vue";

type ScreenComponent = ReturnType<typeof shallowRef>["value"];

interface Screen {
  key: string;
  title: string;
  icon: string;
  group: string;
  component: ScreenComponent;
}

/** ナビに並べる画面定義 (グループ単位)。 */
const screens: Screen[] = [
  { key: "dashboard", title: "ダッシュボード", icon: "mdi-view-dashboard", group: "記帳", component: DashboardView },
  { key: "entry", title: "仕訳入力", icon: "mdi-pencil-plus", group: "記帳", component: JournalEntryForm },
  { key: "cash-book", title: "出納帳", icon: "mdi-cash-register", group: "記帳", component: CashBook },
  { key: "receivables", title: "売上・売掛", icon: "mdi-cash-plus", group: "記帳", component: ReceivableView },
  { key: "expenses", title: "経費", icon: "mdi-cash-minus", group: "記帳", component: ExpenseView },
  { key: "import", title: "CSV取込", icon: "mdi-file-delimited", group: "記帳", component: ImportWizard },
  { key: "journal", title: "仕訳帳", icon: "mdi-book-open-variant", group: "帳簿", component: JournalList },
  { key: "ledger", title: "総勘定元帳", icon: "mdi-book-multiple", group: "帳簿", component: GeneralLedgerView },
  { key: "trial-balance", title: "試算表", icon: "mdi-scale-balance", group: "帳簿", component: TrialBalanceView },
  { key: "pl", title: "損益計算書", icon: "mdi-chart-line", group: "帳簿", component: ProfitAndLossView },
  { key: "bs", title: "貸借対照表", icon: "mdi-chart-box-outline", group: "帳簿", component: BalanceSheetView },
  { key: "fixed-assets", title: "固定資産", icon: "mdi-desktop-classic", group: "決算・申告", component: FixedAssetsView },
  { key: "blue-return", title: "青色申告決算書", icon: "mdi-file-document-outline", group: "決算・申告", component: BlueReturnView },
  { key: "tax", title: "消費税", icon: "mdi-receipt-text-outline", group: "決算・申告", component: TaxView },
  { key: "voucher", title: "証憑保存", icon: "mdi-paperclip", group: "決算・申告", component: VoucherView },
  { key: "data", title: "データ管理", icon: "mdi-database-cog-outline", group: "決算・申告", component: DataManagementView },
];

const groups = ["記帳", "帳簿", "決算・申告"];

const current = ref("dashboard");
const reloadKey = ref(0);
const drawer = ref(true);

const activeScreen = computed(() => screens.find((s) => s.key === current.value) ?? screens[0]);

function select(key: string): void {
  current.value = key;
}

/** 子の作成イベントで再読込キーを進め、仕訳入力からは仕訳帳へ遷移する。 */
function onCreated(): void {
  reloadKey.value += 1;
  if (current.value === "entry") current.value = "journal";
}
</script>

<template>
  <v-app>
    <v-navigation-drawer v-model="drawer" :width="240">
      <v-list-item class="brand" title="会計システム" subtitle="個人事業主向け" />
      <v-divider />
      <template v-for="group in groups" :key="group">
        <v-list-subheader>{{ group }}</v-list-subheader>
        <v-list density="compact" nav>
          <v-list-item
            v-for="screen in screens.filter((s) => s.group === group)"
            :key="screen.key"
            :prepend-icon="screen.icon"
            :title="screen.title"
            :active="current === screen.key"
            @click="select(screen.key)"
          />
        </v-list>
      </template>
    </v-navigation-drawer>

    <v-app-bar :elevation="1" color="primary">
      <v-app-bar-nav-icon @click="drawer = !drawer" />
      <v-app-bar-title>{{ activeScreen.title }}</v-app-bar-title>
      <template #append>
        <span class="app-tag">複式簿記・青色申告対応</span>
      </template>
    </v-app-bar>

    <v-main>
      <v-container>
        <v-card class="pa-4">
          <v-card-title class="text-h6">{{ activeScreen.title }}</v-card-title>
          <v-card-text>
            <!-- 呼び出し時にのみマウント (key で画面切替ごとに再生成) -->
            <component
              :is="activeScreen.component"
              :key="current"
              :reload-key="reloadKey"
              @created="onCreated"
            />
          </v-card-text>
        </v-card>
      </v-container>
    </v-main>
  </v-app>
</template>

<style scoped>
.brand :deep(.v-list-item-title) {
  font-weight: bold;
  font-size: 1.1rem;
}
.app-tag {
  font-size: 0.85rem;
  opacity: 0.9;
  margin-right: 0.5rem;
}
</style>
