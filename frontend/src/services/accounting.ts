/**
 * 会計システムの API クライアント (共通基盤)。
 *
 * 勘定科目・税区分マスタ、仕訳の取得/登録、試算表の取得を提供する。
 * コンポーネントから直接 fetch せず、必ず本サービス経由で通信する。
 *
 * 由来: 全体基本設計 §5 (API 設計規約)。
 */

const BASE_URL = "/api";

/** 勘定科目の5区分。 */
export type AccountType = "asset" | "liability" | "equity" | "revenue" | "expense";

/** 仕訳明細の貸借区分。 */
export type Side = "debit" | "credit";

/** 勘定科目マスタ。 */
export interface Account {
  code: string;
  name: string;
  type: AccountType;
  defaultTaxCode: string | null;
  order: number;
}

/** 税区分マスタ。 */
export interface TaxCategory {
  code: string;
  name: string;
  kind: string;
  ratePercent: number;
  businessType: number | null;
}

/** 仕訳明細。金額は円単位の整数。 */
export interface JournalLine {
  side: Side;
  accountCode: string;
  subAccount?: string | null;
  amount: number;
  taxCode?: string | null;
  taxAmount?: number;
}

/** 仕訳 (複式簿記の基本単位)。 */
export interface JournalEntry {
  id: number;
  date: string;
  description: string;
  fiscalYear: number;
  lines: JournalLine[];
  source: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

/** 仕訳登録リクエスト。 */
export interface JournalEntryCreate {
  date: string;
  description: string;
  lines: JournalLine[];
}

/** 合計残高試算表の1行。 */
export interface TrialBalanceRow {
  accountCode: string;
  accountName: string;
  type: AccountType;
  debitTotal: number;
  creditTotal: number;
  balance: number;
}

/** 合計残高試算表。 */
export interface TrialBalance {
  fiscalYear: number | null;
  rows: TrialBalanceRow[];
  debitTotal: number;
  creditTotal: number;
}

/** 出納帳の1行。 */
export interface CashBookRow {
  date: string;
  description: string;
  counterAccount: string;
  receipt: number;
  payment: number;
  balance: number;
  journalEntryId: number;
}

/** 出納帳 (口座別の入出金と残高)。 */
export interface CashBook {
  accountCode: string;
  accountName: string;
  openingBalance: number;
  rows: CashBookRow[];
  closingBalance: number;
}

/** 出納帳の簡易入力リクエスト。 */
export interface CashEntryRequest {
  accountCode: string;
  direction: "receipt" | "payment";
  counterCode: string;
  amount: number;
  description: string;
  date: string;
  taxCode?: string | null;
}

/** 総勘定元帳の1行。 */
export interface GeneralLedgerRow {
  date: string;
  entryId: number;
  description: string;
  counterAccount: string;
  debitAmount: number;
  creditAmount: number;
  runningBalance: number;
}

/** 総勘定元帳。 */
export interface GeneralLedger {
  accountCode: string;
  accountName: string;
  fiscalYear: number | null;
  openingBalance: number;
  rows: GeneralLedgerRow[];
  closingBalance: number;
}

/** 損益計算書・貸借対照表の1行。 */
export interface ReportRow {
  accountCode: string;
  accountName: string;
  amount: number;
}

/** 損益計算書 (PL)。 */
export interface ProfitAndLoss {
  fiscalYear: number | null;
  revenues: ReportRow[];
  expenses: ReportRow[];
  totalRevenue: number;
  totalExpense: number;
  netIncome: number;
}

/** 貸借対照表 (BS)。 */
export interface BalanceSheet {
  fiscalYear: number | null;
  assets: ReportRow[];
  liabilities: ReportRow[];
  equity: ReportRow[];
  totalAssets: number;
  totalLiabilities: number;
  totalEquity: number;
  netIncome: number;
}

/** 固定資産台帳のレコード。 */
export interface FixedAsset {
  id: number;
  name: string;
  acquisitionDate: string;
  acquisitionCost: number;
  usefulLifeYears: number;
  depreciationMethod: string;
  businessUseRatio: number;
  isSmallAmountSpecial: boolean;
  bookValue: number;
  accumulatedDepreciation: number;
  description: string | null;
  status: string;
  depreciatedYears: number[];
}

/** 固定資産の登録リクエスト。 */
export interface FixedAssetCreate {
  name: string;
  acquisitionDate: string;
  acquisitionCost: number;
  usefulLifeYears: number;
  businessUseRatio?: number;
  useSmallAmountSpecial?: boolean;
  description?: string | null;
}

/** 償却スケジュールの1行。 */
export interface DepreciationEntry {
  fiscalYear: number;
  openingBookValue: number;
  depreciationAmount: number;
  businessDepreciation: number;
  privateDepreciation: number;
  closingBookValue: number;
}

/** 月別売上の1行。 */
export interface MonthlySalesRow {
  month: number;
  amount: number;
}

/** 月別売上集計。 */
export interface MonthlySales {
  fiscalYear: number | null;
  rows: MonthlySalesRow[];
  total: number;
}

/** 青色申告決算書の減価償却明細1行。 */
export interface DepreciationDetail {
  assetName: string;
  acquisitionCost: number;
  usefulLifeYears: number;
  depreciationAmount: number;
  closingBookValue: number;
}

/** 青色申告決算書データ (PL/BS/月別売上/減価償却の集約)。 */
export interface BlueReturn {
  fiscalYear: number;
  profitAndLoss: ProfitAndLoss;
  balanceSheet: BalanceSheet;
  monthlySales: MonthlySales;
  depreciation: DepreciationDetail[];
}

/** ダッシュボードの集約値。 */
export interface Dashboard {
  fiscalYear: number | null;
  revenueTotal: number;
  netIncome: number;
  cashBalance: number;
  receivablesBalance: number;
}

/** CSV 取込の明細 (仕訳候補)。 */
export interface ImportedTransaction {
  id: number;
  date: string;
  description: string;
  payment: number;
  receipt: number;
  balanceRef: number | null;
  suggestedAccountCode: string | null;
  status: string;
  journalEntryId: number | null;
}

/** CSV 取込バッチ。 */
export interface ImportBatch {
  id: number;
  importedAt: string;
  accountCode: string;
  filename: string;
  adapterName: string;
  status: string;
  transactions: ImportedTransaction[];
}

/** CSV 取込リクエスト。 */
export interface ImportRequest {
  accountCode: string;
  csvText: string;
  adapter?: string;
  filename?: string;
}

/** 税率別の消費税集計。 */
export interface TaxRateLine {
  ratePercent: number;
  taxCode: string;
  taxableSalesBase: number;
  taxAmount: number;
  deductibleAmount: number;
  payableAmount: number;
}

/** 消費税 (簡易課税) 集計結果。 */
export interface ConsumptionTax {
  fiscalYear: number;
  businessType: number;
  deemedPurchaseRate: number;
  taxRates: TaxRateLine[];
  totalTaxAmount: number;
  totalDeductibleAmount: number;
  totalPayableAmount: number;
}

/** 証憑。 */
export interface Voucher {
  id: number;
  transactionDate: string;
  amount: number;
  counterparty: string;
  fileName: string;
  contentBase64: string | null;
  journalEntryId: number | null;
  createdAt: string;
}

/** 証憑の登録リクエスト。 */
export interface VoucherCreate {
  transactionDate: string;
  amount: number;
  counterparty: string;
  fileName: string;
}

/** 証憑の検索条件。 */
export interface VoucherSearch {
  dateFrom?: string;
  dateTo?: string;
  amount?: number;
  counterparty?: string;
}

/** 年度繰越のドライラン結果。 */
export interface YearEndPreview {
  fiscalYear: number;
  nextFiscalYear: number;
  balanceForward: {
    accountCode: string;
    accountName: string;
    accountType: string;
    closingBalance: number;
  }[];
  netIncome: number;
  openingCapitalNext: number;
}

/** 売上計上リクエスト (発生主義)。 */
export interface SalesRequest {
  counterparty: string;
  amount: number;
  date: string;
  description: string;
  taxCode?: string;
}

/** 売掛入金消込リクエスト。 */
export interface ReceivablePaymentRequest {
  counterparty: string;
  amount: number;
  date: string;
  description?: string;
  depositAccountCode?: string;
}

/** 取引先別の未入金 (売掛残)。 */
export interface OutstandingRow {
  counterparty: string;
  balance: number;
}

/** 経費入力リクエスト。 */
export interface ExpenseRequest {
  expenseAccountCode: string;
  amount: number;
  creditAccountCode: string;
  taxCode?: string | null;
  description: string;
  date: string;
  counterparty?: string | null;
}

/** 未払金の支払消込リクエスト。 */
export interface PayablePaymentRequest {
  counterparty: string;
  amount: number;
  date: string;
  description?: string;
  depositAccountCode?: string;
}

/** 取引先別の未払金残高。 */
export interface PayableRow {
  counterparty: string;
  balance: number;
}

/** snake_case の API レスポンスを camelCase に変換しつつ JSON を取得する。 */
async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return camelize(await res.json()) as T;
}

/** 勘定科目マスタを取得する。 */
export async function fetchAccounts(): Promise<Account[]> {
  return getJson<Account[]>("/accounts");
}

/** 税区分マスタを取得する。 */
export async function fetchTaxCategories(): Promise<TaxCategory[]> {
  return getJson<TaxCategory[]>("/tax-categories");
}

/** 仕訳一覧を取得する。`fiscalYear` 指定でその年度に絞り込む。 */
export async function fetchJournalEntries(fiscalYear?: number): Promise<JournalEntry[]> {
  const query = fiscalYear ? `?fiscal_year=${fiscalYear}` : "";
  return getJson<JournalEntry[]>(`/journal-entries${query}`);
}

/** 合計残高試算表を取得する。 */
export async function fetchTrialBalance(fiscalYear?: number): Promise<TrialBalance> {
  const query = fiscalYear ? `?fiscal_year=${fiscalYear}` : "";
  return getJson<TrialBalance>(`/reports/trial-balance${query}`);
}

/** 出納帳を取得する。 */
export async function fetchCashBook(accountCode: string, fiscalYear?: number): Promise<CashBook> {
  const query = fiscalYear ? `?fiscal_year=${fiscalYear}` : "";
  return getJson<CashBook>(`/cash-book/${accountCode}${query}`);
}

/** 総勘定元帳を取得する。 */
export async function fetchGeneralLedger(
  accountCode: string,
  fiscalYear?: number,
): Promise<GeneralLedger> {
  const year = fiscalYear ? `&fiscal_year=${fiscalYear}` : "";
  return getJson<GeneralLedger>(`/reports/general-ledger?account_code=${accountCode}${year}`);
}

/** 損益計算書を取得する。 */
export async function fetchProfitAndLoss(fiscalYear?: number): Promise<ProfitAndLoss> {
  const query = fiscalYear ? `?fiscal_year=${fiscalYear}` : "";
  return getJson<ProfitAndLoss>(`/reports/pl${query}`);
}

/** 貸借対照表を取得する。 */
export async function fetchBalanceSheet(fiscalYear?: number): Promise<BalanceSheet> {
  const query = fiscalYear ? `?fiscal_year=${fiscalYear}` : "";
  return getJson<BalanceSheet>(`/reports/bs${query}`);
}

/** POST して camelCase 化したレスポンスを返す共通ヘルパー。 */
async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(snakeize(payload)),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `API error: ${res.status}`);
  }
  return camelize(await res.json()) as T;
}

/** 仕訳を登録する。借貸不一致は API が 422 を返す。 */
export async function createJournalEntry(payload: JournalEntryCreate): Promise<JournalEntry> {
  return postJson<JournalEntry>("/journal-entries", payload);
}

/** 出納帳の簡易入力 (入金/出金) を登録する。裏で複式仕訳に変換される。 */
export async function createCashEntry(payload: CashEntryRequest): Promise<JournalEntry> {
  return postJson<JournalEntry>("/cash-book/entries", payload);
}

/** 固定資産台帳の一覧を取得する。 */
export async function fetchFixedAssets(): Promise<FixedAsset[]> {
  return getJson<FixedAsset[]>("/fixed-assets");
}

/** 固定資産を登録する。 */
export async function createFixedAsset(payload: FixedAssetCreate): Promise<FixedAsset> {
  return postJson<FixedAsset>("/fixed-assets", payload);
}

/** 固定資産の償却スケジュールを取得する。 */
export async function fetchDepreciationSchedule(assetId: number): Promise<DepreciationEntry[]> {
  return getJson<DepreciationEntry[]>(`/fixed-assets/${assetId}/depreciation-schedule`);
}

/** 指定年度の減価償却を仕訳計上する。 */
export async function postDepreciation(assetId: number, fiscalYear: number): Promise<JournalEntry> {
  return postJson<JournalEntry>(
    `/fixed-assets/${assetId}/depreciation?fiscal_year=${fiscalYear}`,
    {},
  );
}

/** 月別売上集計を取得する。 */
export async function fetchMonthlySales(fiscalYear: number): Promise<MonthlySales> {
  return getJson<MonthlySales>(`/reports/monthly-sales?fiscal_year=${fiscalYear}`);
}

/** 青色申告決算書データを取得する。 */
export async function fetchBlueReturn(fiscalYear: number): Promise<BlueReturn> {
  return getJson<BlueReturn>(`/closing/blue-return?fiscal_year=${fiscalYear}`);
}

/** ダッシュボードの集約値を取得する。 */
export async function fetchDashboard(fiscalYear?: number): Promise<Dashboard> {
  const query = fiscalYear ? `?fiscal_year=${fiscalYear}` : "";
  return getJson<Dashboard>(`/reports/dashboard${query}`);
}

/** CSV 明細を取り込み、仕訳候補のバッチを返す。 */
export async function importCsv(payload: ImportRequest): Promise<ImportBatch> {
  return postJson<ImportBatch>("/imports/csv", payload);
}

/** 取込バッチの最新状態を取得する。 */
export async function fetchImportBatch(batchId: number): Promise<ImportBatch> {
  return getJson<ImportBatch>(`/imports/${batchId}`);
}

/** 取込明細を確定し、複式仕訳に変換する。相手科目を上書き指定できる。 */
export async function confirmImportedTransaction(
  batchId: number,
  txId: number,
  counterCode?: string,
): Promise<JournalEntry> {
  return postJson<JournalEntry>(`/imports/${batchId}/transactions/${txId}/confirm`, {
    counterCode: counterCode ?? null,
  });
}

/** 取込明細をスキップする。 */
export async function skipImportedTransaction(
  batchId: number,
  txId: number,
): Promise<ImportedTransaction> {
  return postJson<ImportedTransaction>(`/imports/${batchId}/transactions/${txId}/skip`, {});
}

/** 消費税 (簡易課税) 集計を取得する。 */
export async function fetchConsumptionTax(fiscalYear: number): Promise<ConsumptionTax> {
  return getJson<ConsumptionTax>(`/tax/consumption?fiscal_year=${fiscalYear}`);
}

/** 消費税の納付額を確定し仕訳を計上する。 */
export async function finalizeConsumptionTax(fiscalYear: number): Promise<JournalEntry> {
  const res = await postJson<{ journalEntry: JournalEntry }>(
    `/tax/consumption/finalize?fiscal_year=${fiscalYear}`,
    {},
  );
  return res.journalEntry;
}

/** 証憑を登録する。 */
export async function createVoucher(payload: VoucherCreate): Promise<Voucher> {
  return postJson<Voucher>("/vouchers", payload);
}

/** 証憑を電帳法の3キー (取引日・金額・取引先) で検索する。 */
export async function searchVouchers(search: VoucherSearch): Promise<Voucher[]> {
  const params = new URLSearchParams();
  if (search.dateFrom) params.set("date_from", search.dateFrom);
  if (search.dateTo) params.set("date_to", search.dateTo);
  if (search.amount !== undefined) params.set("amount", String(search.amount));
  if (search.counterparty) params.set("counterparty", search.counterparty);
  const query = params.toString();
  return getJson<Voucher[]>(`/vouchers${query ? `?${query}` : ""}`);
}

/** 帳簿・決算書の CSV ダウンロード URL を返す。 */
export function exportUrl(report: string, fiscalYear?: number): string {
  const year = fiscalYear ? `&fiscal_year=${fiscalYear}` : "";
  return `${BASE_URL}/export/${report}?format=csv${year}`;
}

/** 年度繰越のドライランを取得する。 */
export async function fetchCarryForwardPreview(fiscalYear: number): Promise<YearEndPreview> {
  return getJson<YearEndPreview>(`/year-end/carry-forward/preview?fiscal_year=${fiscalYear}`);
}

/** 年度繰越を実行する。 */
export async function executeCarryForward(fiscalYear: number): Promise<JournalEntry> {
  const res = await postJson<{ openingEntry: JournalEntry }>(
    `/year-end/carry-forward?fiscal_year=${fiscalYear}`,
    {},
  );
  return res.openingEntry;
}

/** 売上を計上する (発生主義)。 */
export async function createSales(payload: SalesRequest): Promise<JournalEntry> {
  return postJson<JournalEntry>("/receivables/sales", payload);
}

/** 売掛金の入金を消し込む。 */
export async function createReceivablePayment(
  payload: ReceivablePaymentRequest,
): Promise<JournalEntry> {
  return postJson<JournalEntry>("/receivables/payment", payload);
}

/** 取引先別の未入金 (売掛残) 一覧を取得する。 */
export async function fetchOutstanding(): Promise<OutstandingRow[]> {
  return getJson<OutstandingRow[]>("/receivables/outstanding");
}

/** 経費を計上する。 */
export async function createExpense(payload: ExpenseRequest): Promise<JournalEntry> {
  return postJson<JournalEntry>("/expenses", payload);
}

/** 未払金を支払って消し込む。 */
export async function payPayable(payload: PayablePaymentRequest): Promise<JournalEntry> {
  return postJson<JournalEntry>("/expenses/payment", payload);
}

/** 取引先別の未払金残高一覧を取得する。 */
export async function fetchPayables(): Promise<PayableRow[]> {
  return getJson<PayableRow[]>("/expenses/payables");
}

// --- ケース変換ユーティリティ (API は snake_case、フロントは camelCase) ---

function toCamel(key: string): string {
  return key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
}

function toSnake(key: string): string {
  return key.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`);
}

function camelize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(camelize);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([k, v]) => [toCamel(k), camelize(v)]),
    );
  }
  return value;
}

function snakeize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(snakeize);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([k, v]) => [toSnake(k), snakeize(v)]),
    );
  }
  return value;
}
