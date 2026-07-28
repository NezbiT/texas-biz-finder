/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import { VitePWA } from "vite-plugin-pwa";
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin';
import { playwright } from '@vitest/browser-playwright';
const dirname = typeof __dirname !== 'undefined' ? __dirname : path.dirname(fileURLToPath(import.meta.url));

const isStorybook =
  process.env.npm_lifecycle_event === "storybook" ||
  process.env.npm_lifecycle_event === "build-storybook";

// More info at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon
export default defineConfig(({ mode }) => {
  const fileEnv = loadEnv(mode, dirname, "");
  const apiProxyTarget =
    fileEnv.VITE_API_PROXY_TARGET || process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
  plugins: [
    vue(),
    ...(isStorybook
      ? []
      : [
          VitePWA({
    registerType: "autoUpdate",
    includeAssets: ["favicon.svg", "apple-touch-icon.png", "pwa-192.png", "pwa-512.png"],
    manifest: {
      name: "TxBizFinder Intelligence",
      short_name: "TxBizFinder",
      description:
        "Texas suite: business leads, Houston permits, Ship Channel air, emissions. Four apps. One map.",
      theme_color: "#0c1222",
      background_color: "#0c1222",
      display: "standalone",
      orientation: "portrait-primary",
      scope: "/",
      start_url: "/",
      id: "/",
      lang: "en",
      categories: ["business", "productivity"],
      icons: [{
        src: "pwa-192.png",
        sizes: "192x192",
        type: "image/png"
      }, {
        src: "pwa-512.png",
        sizes: "512x512",
        type: "image/png"
      }, {
        src: "maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable"
      }]
    },
    workbox: {
      // Silence "Router is responding to… / PrecacheRoute" spam in the console
      disableDevLogs: true,
      globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2,webmanifest}"],
      runtimeCaching: [{
        urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
        handler: "CacheFirst",
        options: {
          cacheName: "google-fonts-stylesheets",
          expiration: {
            maxEntries: 10,
            maxAgeSeconds: 60 * 60 * 24 * 365
          }
        }
      }, {
        urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
        handler: "CacheFirst",
        options: {
          cacheName: "google-fonts-webfonts",
          expiration: {
            maxEntries: 20,
            maxAgeSeconds: 60 * 60 * 24 * 365
          }
        }
      }, {
        urlPattern: /\/api\/.*/i,
        handler: "NetworkFirst",
        options: {
          cacheName: "txbizfinder-api",
          networkTimeoutSeconds: 8,
          expiration: {
            maxEntries: 32,
            maxAgeSeconds: 60 * 5
          }
        }
      }]
    },
    // No service worker in `npm run dev` — keeps console clean; SW only on build/prod
    devOptions: {
      enabled: false,
      disableDevLogs: true,
    }
          }),
        ]),
  ],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true
      }
    }
  },
  test: {
    projects: [{
      extends: true,
      plugins: [
      // The plugin will run tests for the stories defined in your Storybook config
      // See options at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon#storybooktest
      storybookTest({
        configDir: path.join(dirname, '.storybook')
      })],
      test: {
        name: 'storybook',
        browser: {
          enabled: true,
          headless: true,
          provider: playwright({}),
          instances: [{
            browser: 'chromium'
          }]
        }
      }
    }]
  }
};
});