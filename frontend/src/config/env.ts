/**
 * Single source of truth for Vite public env (VITE_*).
 * Backend secrets stay in repo-root `.env` (FastAPI); this file is frontend-only.
 */

function read(key: keyof ImportMetaEnv, fallback = ""): string {
  const value = import.meta.env[key];
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

/** Strip trailing slash so path joins stay clean. */
function stripSlash(url: string): string {
  return url.replace(/\/+$/, "");
}

export const env = {
  /** Same value as backend ADMIN_API_KEY (header X-API-Key). */
  adminApiKey: read("VITE_ADMIN_API_KEY", "admin-dev-key-change-me"),

  /**
   * Optional absolute API origin (e.g. https://api.txbizfinder.com).
   * Empty → same-origin `/api/...` (Vite proxy in dev, FastAPI mount in prod).
   */
  apiBaseUrl: stripSlash(read("VITE_API_BASE_URL", "")),

  /** Suite product URLs / paths — override per environment. */
  suite: {
    wwwUrl: stripSlash(read("VITE_SUITE_WWW_URL", "https://www.txbizfinder.com")),
    bizAppPath: read("VITE_SUITE_BIZ_APP_PATH", "/app") || "/app",
    radarUrl: stripSlash(read("VITE_SUITE_RADAR_URL", "https://radar.txbizfinder.com")),
    channelUrl: stripSlash(read("VITE_SUITE_CHANNEL_URL", "https://channel.txbizfinder.com")),
    sentinelUrl: stripSlash(read("VITE_SUITE_SENTINEL_URL", "https://sentinel.txbizfinder.com")),
    floodUrl: stripSlash(read("VITE_SUITE_FLOOD_URL", "https://flood.txbizfinder.com")),
    powerUrl: stripSlash(read("VITE_SUITE_POWER_URL", "https://power.txbizfinder.com")),
    mapUrl: stripSlash(read("VITE_SUITE_MAP_URL", "https://map.txbizfinder.com")),
  },
} as const;

export type AppEnv = typeof env;
