<script setup lang="ts">
/**
 * 会計システムのシェル。Phase 1 (記帳基盤) の各機能をタブで切り替える。
 *
 * 由来: 全体基本設計 §1.1 (SPA + BFF) / マイルストーン Phase 1。
 */
import { ref } from "vue";
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
import DataManagementView from "@/components/DataManagementView.vue";

type Tab =
  | "dashboard"
  | "entry"
  | "cash-book"
  | "import"
  | "journal"
  | "ledger"
  | "trial-balance"
  | "pl"
  | "bs"
  | "fixed-assets"
  | "blue-return"
  | "tax"
  | "voucher"
  | "data";
const tabs: { key: Tab; label: string }[] = [
  { key: "dashboard", label: "ダッシュボード" },
  { key: "entry", label: "仕訳入力" },
  { key: "cash-book", label: "出納帳" },
  { key: "import", label: "CSV取込" },
  { key: "journal", label: "仕訳帳" },
  { key: "ledger", label: "総勘定元帳" },
  { key: "trial-balance", label: "試算表" },
  { key: "pl", label: "損益計算書" },
  { key: "bs", label: "貸借対照表" },
  { key: "fixed-assets", label: "固定資産" },
  { key: "blue-return", label: "青色申告決算書" },
  { key: "tax", label: "消費税" },
  { key: "voucher", label: "証憑保存" },
  { key: "data", label: "データ管理" },
];
const tab = ref<Tab>("dashboard");
const reloadKey = ref(0);

function onCreated(next: Tab = "journal") {
  reloadKey.value += 1;
  tab.value = next;
}
</script>

<template>
  <div class="app">
    <header>
      <h1>会計システム</h1>
      <p class="subtitle">個人事業主向け / 複式簿記・青色申告対応</p>
    </header>

    <nav>
      <button
        v-for="t in tabs"
        :key="t.key"
        :class="{ active: tab === t.key }"
        @click="tab = t.key"
      >
        {{ t.label }}
      </button>
    </nav>

    <main>
      <section v-show="tab === 'dashboard'">
        <h2>ダッシュボード</h2>
        <DashboardView :reload-key="reloadKey" />
      </section>
      <section v-show="tab === 'entry'">
        <h2>仕訳入力</h2>
        <JournalEntryForm @created="onCreated('journal')" />
      </section>
      <section v-show="tab === 'cash-book'">
        <h2>出納帳</h2>
        <CashBook :reload-key="reloadKey" @created="reloadKey++" />
      </section>
      <section v-show="tab === 'import'">
        <h2>CSV明細取込</h2>
        <ImportWizard @created="reloadKey++" />
      </section>
      <section v-show="tab === 'journal'">
        <h2>仕訳帳</h2>
        <JournalList :reload-key="reloadKey" />
      </section>
      <section v-show="tab === 'ledger'">
        <h2>総勘定元帳</h2>
        <GeneralLedgerView :reload-key="reloadKey" />
      </section>
      <section v-show="tab === 'trial-balance'">
        <h2>合計残高試算表</h2>
        <TrialBalanceView :reload-key="reloadKey" />
      </section>
      <section v-show="tab === 'pl'">
        <h2>損益計算書</h2>
        <ProfitAndLossView :reload-key="reloadKey" />
      </section>
      <section v-show="tab === 'bs'">
        <h2>貸借対照表</h2>
        <BalanceSheetView :reload-key="reloadKey" />
      </section>
      <section v-show="tab === 'fixed-assets'">
        <h2>固定資産・減価償却</h2>
        <FixedAssetsView @created="reloadKey++" />
      </section>
      <section v-show="tab === 'blue-return'">
        <h2>青色申告決算書</h2>
        <BlueReturnView :reload-key="reloadKey" />
      </section>
      <section v-show="tab === 'tax'">
        <h2>消費税 (簡易課税)</h2>
        <TaxView @created="reloadKey++" />
      </section>
      <section v-show="tab === 'voucher'">
        <h2>証憑保存 (電帳法)</h2>
        <VoucherView />
      </section>
      <section v-show="tab === 'data'">
        <h2>データ管理</h2>
        <DataManagementView @created="reloadKey++" />
      </section>
    </main>
  </div>
</template>

<style scoped>
.app {
  max-width: 960px;
  margin: 0 auto;
  padding: 1.5rem;
}
header h1 {
  margin-bottom: 0.25rem;
}
.subtitle {
  color: #6b7280;
  margin-top: 0;
}
nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  border-bottom: 2px solid #e5e7eb;
  margin-bottom: 1rem;
}
nav button {
  background: none;
  border: none;
  padding: 0.5rem 1rem;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}
nav button.active {
  border-bottom-color: #2563eb;
  color: #2563eb;
  font-weight: bold;
}
</style>
