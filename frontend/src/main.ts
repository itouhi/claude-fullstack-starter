import { createApp } from "vue";

import "vuetify/styles";
import "@mdi/font/css/materialdesignicons.css";
import { createVuetify } from "vuetify";

import App from "./App.vue";
import "./style.css";

// コンポーネント/ディレクティブは vite-plugin-vuetify の autoImport が自動登録する
const vuetify = createVuetify({
  icons: { defaultSet: "mdi" },
});

createApp(App).use(vuetify).mount("#app");
