import { createRouter, createWebHistory } from "vue-router";
import SuiteLanding from "./components/SuiteLanding.vue";
import LeadsDashboard from "./components/LeadsDashboard.vue";
import { BIZ_APP_PATH } from "./config/suite";

const bizPath = BIZ_APP_PATH.startsWith("/") ? BIZ_APP_PATH : `/${BIZ_APP_PATH}`;

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "landing",
      component: SuiteLanding,
      meta: { titleKey: "landingDocTitle" },
    },
    {
      path: bizPath,
      name: "app",
      component: LeadsDashboard,
      meta: { titleKey: "appDocTitle" },
    },
    // Back-compat aliases
    { path: "/leads", redirect: bizPath },
    ...(bizPath !== "/app" ? [{ path: "/app", redirect: bizPath }] : []),
  ],
  scrollBehavior() {
    return { top: 0 };
  },
});

export default router;
