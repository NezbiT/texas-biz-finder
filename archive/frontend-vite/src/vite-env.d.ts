/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  readonly VITE_ADMIN_API_KEY?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_PROXY_TARGET?: string;
  readonly VITE_SUITE_WWW_URL?: string;
  readonly VITE_SUITE_BIZ_APP_PATH?: string;
  readonly VITE_SUITE_RADAR_URL?: string;
  readonly VITE_SUITE_CHANNEL_URL?: string;
  readonly VITE_SUITE_SENTINEL_URL?: string;
  readonly VITE_SUITE_FLOOD_URL?: string;
  readonly VITE_SUITE_POWER_URL?: string;
  readonly VITE_SUITE_MAP_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
