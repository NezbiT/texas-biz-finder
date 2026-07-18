import { createApp } from "vue";
import { registerSW } from "virtual:pwa-register";
import App from "./App.vue";
import router from "./router";
import "./style.css";

// PWA service worker only in production builds (avoids Workbox debug spam in dev)
if (import.meta.env.PROD) {
  registerSW({
    immediate: true,
    onRegisteredSW(_url, registration) {
      if (registration) {
        window.setInterval(() => registration.update(), 60 * 60 * 1000);
      }
    },
  });
}

createApp(App).use(router).mount("#app");