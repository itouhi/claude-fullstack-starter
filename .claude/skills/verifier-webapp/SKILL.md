---
name: verifier-webapp
description: フロントエンド(Vue)/API の変更を実ブラウザ(Playwright+Chromium headless)で動作確認する。backend(8000)+frontend(5173)を起動し、画面描画・API ステータス・コンソールエラーを観測してスクショを残す。「UI をブラウザで確認」「動作確認」「verify UI」などで起動。汎用 verify スキルからも verifier-* として検出される。
---

# verifier-webapp

このプロジェクト (FastAPI + Vue 3 + Vite) の **UI/E2E をランタイム観測で検証**するためのプロトコル。
ユニットテストや型チェックの再実行ではなく、**実際にアプリを起動して実ブラウザで駆動**し、見えたものを証拠として残す。

## 何を検証するか
- frontend コンポーネント / 画面の変更が実画面で正しく描画されるか
- フロント→`services/`→`/api/*` (Vite proxy 経由) の通信が成立するか
- loading / error などの状態遷移が機能するか
- **サービス層** (`compose-service`): ナビの**ルート遷移**で対象機能が描画され、集約 (`/dashboard`) が表示されるか。
  `ACTIONS` で `{"click":"nav a[href=\"/products\"]"}` のようにナビをクリックし、遷移後のセレクタを `waitFor` する。

## 前提セットアップ (初回のみ詰まりやすい)
`playwright` は frontend の **devDependency に常設済み** (`npm install` で入る)。都度の install/uninstall は不要。
初回環境では **ブラウザ本体とシステム依存**だけ用意する:
1. **Chromium 本体** (npm パッケージとは別にバイナリ取得が必要):
   ```
   cd frontend && npx playwright install chromium
   ```
2. **Chromium のシステム依存ライブラリ** (`libatk-1.0.so.0` 等が無いと起動失敗):
   ```
   sudo "$(which node)" frontend/node_modules/playwright/cli.js install-deps chromium
   ```
   > `sudo npx ...` は PATH に npx が無く失敗する。`$(which node)` で絶対パス起動する。
   > いずれもマシンに一度入れれば以降は不要。
3. **トークン等の env**: 認証がある場合 `cp frontend/.env.example frontend/.env.local` し、backend の値と一致させる (例: `VITE_API_TOKEN`)。
   > `import.meta.env.VITE_*` はビルド時に埋め込まれるため、env は dev サーバ起動**前**に用意する。

## 手順
> サーバは**ターン跨ぎで生存する形で起動**する (Claude Code の場合は Bash の `run_in_background: true`)。
> 通常の `&`/`nohup` はツール呼び出し終了時に取りこぼされ、次の駆動で接続不能になりやすい。
> 起動前に既存プロセスを一掃する: `pkill -9 -f "uvicorn app.main"; pkill -9 -f vite`。

1. **backend 起動** (8000、バックグラウンド):
   ```
   cd backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 >/tmp/backend.log 2>&1
   ```
   `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health` が 200 になるまで待つ。
2. **frontend 起動** (5173、バックグラウンド):
   ```
   cd frontend && npm run dev -- --host --port 5173 --strictPort >/tmp/frontend.log 2>&1
   ```
   `http://127.0.0.1:5173/` が 200 になるまで待つ。**起動エラーは `/tmp/frontend.log` を必ず確認** (例: `@` エイリアス未設定で 500)。
   > `--strictPort` で 5173 が空いていないと即失敗させる (黙って別ポートに逃げると駆動先がズレる)。`/tmp/frontend.log` の `Local:` 行で実ポートを確認するのも可。
3. **実ブラウザで駆動**: 同梱スクリプトを使う (**リポジトリルートで実行**。`playwright` は cwd 起点で自動解決される)。
   ```
   URL="http://localhost:5173" WAIT_SELECTOR=".users-list" API_MATCH="/api/" \
   SHOT="/tmp/verify-shot.png" \
   node .claude/skills/verifier-webapp/scripts/drive.cjs
   ```
   出力 JSON の `apiStatuses` (`method`/`status`)、`consoleErrors` (空か)、`bodyText` (期待文字列が含まれるか) を確認し、`screenshot` を Read して目視する。
   > playwright が別の場所にある場合のみ `PW=/abs/path/to/playwright` で明示できる。
4. **対話プローブ** (フォーム入力・送信などの操作を検証する場合): `ACTIONS` に操作の JSON 配列を渡す。初期描画後に順に実行される。
   ```
   URL="http://localhost:5173" WAIT_SELECTOR=".tasks" API_MATCH="/api/tasks" SHOT="/tmp/add.png" \
   ACTIONS='[{"fill":{"selector":".tasks input","value":"牛乳"}},{"click":".tasks button[type=submit]"},{"waitFor":".tasks li"}]' \
   node .claude/skills/verifier-webapp/scripts/drive.cjs
   ```
   `apiStatuses` に POST が 201 で記録され、`bodyText` に追加結果が反映されているかを確認する。
   操作種別: `fill`{selector,value} / `click`(selector) / `waitFor`(selector) / `waitTimeout`(ms)。
5. **プローブ (最低1つ)**: ハッピーパス以外を1つ崩す。例: backend を止めて再駆動し、error 状態が描画されるか確認。
   ```
   pkill -9 -f "uvicorn app.main:app"   # 全プロセス。reloader が子を産むので -f で確実に
   ```
   確認後は backend を再起動して環境を健全化する。
6. **teardown**: `pkill -9 -f "uvicorn app.main:app"; pkill -9 -f vite`
7. **報告**: PASS / FAIL と、観測値・スクショパス・気づきを述べる。

## ハマりどころ (実地で潰した知見)
- **`@` エイリアス**: `vite.config.ts` に `resolve.alias['@']='./src'` が無いと `@/...` import が解決できず dev が 500。
- **Chromium 依存ライブラリ**: `install-deps` を `$(which node)` 経由の sudo で入れる。
- **サーバの止め残し**: `kill <pid>` だと取り逃すことがある。`pkill -f` で全停止し、`curl` が `000`(connection refused) になるまで確認する。
- **ポート競合**: 旧 vite が 5173 を掴んでいると新 vite が 5174.. に逃げ、駆動先がズレる。起動前に `pkill -f vite` で一掃し、`--strictPort` で固定する。
- **バックグラウンド起動の取りこぼし**: 通常の `&`/`nohup` はツール終了時に消えることがある。`run_in_background` 等のターン跨ぎ生存する方式で起動する。
- **env はビルド前**: `.env.local` を作る前に dev サーバを起動するとトークンが空のまま埋め込まれる。

## ガードレール
- **テスト/型チェックの再実行で代替しない**。これは CI の再現であって動作確認ではない。必ずアプリを起動して観測する。
- スクショ・JSON 出力など**captured な証拠**を残す。記憶で報告しない。
- 曖昧な出力は FAIL とし、生の出力を添える。
- `playwright` は frontend の devDependency に常設済み。撤去しない (都度 install/uninstall の摩擦を避けるため)。ブラウザ本体とシステム依存はマシンに一度入れれば再利用される。
