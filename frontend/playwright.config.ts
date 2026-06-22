import { defineConfig, devices } from "@playwright/test";

/**
 * 会計システムの E2E テスト設定。
 *
 * backend (8000, in-memory) と frontend (5173) を webServer で自動起動する。
 * backend は DATABASE_URL を設定しない = in-memory で起動し、毎回まっさらな状態から
 * 始まるため、テストは決定的になる。
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // backend ストアはプロセス共有のため直列実行で決定性を保つ
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "list" : [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    // 実施中の画面を録画 (webm)。mp4 へは別途 ffmpeg で変換する
    video: { mode: "on", size: { width: 1280, height: 720 } },
    viewport: { width: 1280, height: 720 },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "bash -c 'cd ../backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000'",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "npm run dev -- --host --port 5173 --strictPort",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
