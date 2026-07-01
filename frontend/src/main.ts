import { createApp } from "vue";
import { registerSW } from "virtual:pwa-register";
import App from "./App.vue";
import "./style.css";

registerSW({
  immediate: true,
  onRegisteredSW(_url, registration) {
    if (registration) {
      window.setInterval(() => registration.update(), 60 * 60 * 1000);
    }
  },
});

createApp(App).mount("#app");