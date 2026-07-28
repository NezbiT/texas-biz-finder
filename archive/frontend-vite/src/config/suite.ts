/**
 * TxBizFinder Intelligence — product catalog.
 * Domains/URLs come from env; copy keys point at i18n catalogs.
 */
import type { MessageKey } from "../i18n/en";
import { env } from "./env";

export type SuiteProductId =
  | "biz"
  | "radar"
  | "channel"
  | "sentinel"
  | "flood"
  | "power"
  | "map";

export type SuiteProduct = {
  id: SuiteProductId;
  domain: string;
  /** Absolute URL or in-app path */
  href: string;
  external: boolean;
  nameKey: MessageKey;
  blurbKey: MessageKey;
  ctaKey: MessageKey;
  accent: string;
  ring: string;
};

function hostLabel(urlOrPath: string, fallback: string): string {
  if (urlOrPath.startsWith("http://") || urlOrPath.startsWith("https://")) {
    try {
      return new URL(urlOrPath).host;
    } catch {
      return fallback;
    }
  }
  return fallback;
}

const { suite } = env;

export const SUITE_PRODUCTS: readonly SuiteProduct[] = [
  {
    id: "biz",
    domain: hostLabel(suite.wwwUrl, "www.txbizfinder.com"),
    href: suite.bizAppPath.startsWith("/") ? suite.bizAppPath : `/${suite.bizAppPath}`,
    external: false,
    nameKey: "productBizName",
    blurbKey: "productBizBlurb",
    ctaKey: "productBizCta",
    accent: "from-orange-500/25 to-orange-500/5",
    ring: "hover:border-orange-400/50",
  },
  {
    id: "radar",
    domain: hostLabel(suite.radarUrl, "radar.txbizfinder.com"),
    href: suite.radarUrl,
    external: true,
    nameKey: "productRadarName",
    blurbKey: "productRadarBlurb",
    ctaKey: "productRadarCta",
    accent: "from-orange-600/20 to-orange-600/5",
    ring: "hover:border-orange-500/50",
  },
  {
    id: "channel",
    domain: hostLabel(suite.channelUrl, "channel.txbizfinder.com"),
    href: suite.channelUrl,
    external: true,
    nameKey: "productChannelName",
    blurbKey: "productChannelBlurb",
    ctaKey: "productChannelCta",
    accent: "from-amber-400/20 to-amber-400/5",
    ring: "hover:border-amber-400/50",
  },
  {
    id: "sentinel",
    domain: hostLabel(suite.sentinelUrl, "sentinel.txbizfinder.com"),
    href: suite.sentinelUrl,
    external: true,
    nameKey: "productSentinelName",
    blurbKey: "productSentinelBlurb",
    ctaKey: "productSentinelCta",
    accent: "from-amber-500/25 to-amber-500/5",
    ring: "hover:border-amber-500/50",
  },
  {
    id: "flood",
    domain: hostLabel(suite.floodUrl, "flood.txbizfinder.com"),
    href: suite.floodUrl,
    external: true,
    nameKey: "productFloodName",
    blurbKey: "productFloodBlurb",
    ctaKey: "productFloodCta",
    accent: "from-sky-500/25 to-sky-500/5",
    ring: "hover:border-sky-400/50",
  },
  {
    id: "power",
    domain: hostLabel(suite.powerUrl, "power.txbizfinder.com"),
    href: suite.powerUrl,
    external: true,
    nameKey: "productPowerName",
    blurbKey: "productPowerBlurb",
    ctaKey: "productPowerCta",
    accent: "from-yellow-500/25 to-yellow-500/5",
    ring: "hover:border-yellow-400/50",
  },
  {
    id: "map",
    domain: hostLabel(suite.mapUrl, "map.txbizfinder.com"),
    href: suite.mapUrl,
    external: true,
    nameKey: "productMapName",
    blurbKey: "productMapBlurb",
    ctaKey: "productMapCta",
    accent: "from-orange-400/30 to-amber-500/10",
    ring: "hover:border-orange-300/60",
  },
] as const;

/** Star tip order (outer ring). MAP sits in the center, not on a tip. */
export const STAR_TIP_ORDER: readonly SuiteProductId[] = [
  "flood",
  "biz",
  "radar",
  "channel",
  "sentinel",
  "power",
] as const;

export const SUITE_STEPS = [
  { title: "suiteHowStep1", body: "suiteHowStep1Body" },
  { title: "suiteHowStep2", body: "suiteHowStep2Body" },
  { title: "suiteHowStep3", body: "suiteHowStep3Body" },
  { title: "suiteHowStep4", body: "suiteHowStep4Body" },
] as const satisfies ReadonlyArray<{ title: MessageKey; body: MessageKey }>;

export const BIZ_APP_PATH = SUITE_PRODUCTS[0].href;
export const SUITE_HOME_PATH = "/";

/** Creator credit — shown in footers across the suite (not as a product tip). */
export const SUITE_CREATOR = {
  name: "Mario Alvarez",
  url: "https://mariosalvarez.com",
  host: "mariosalvarez.com",
} as const;

/** Product display names (full brands — portals, footer, marquee). */
export const SUITE_PRODUCT_LABELS: Record<SuiteProductId, string> = {
  biz: "TxBizFinder",
  radar: "PermitRadar",
  channel: "ChannelWatch",
  sentinel: "Emissions Sentinel",
  flood: "FloodGuard Texas",
  power: "PowerPulse Texas",
  map: "Map Hub Texas",
};

/** Short labels on the landing star tips only. */
export const STAR_TIP_LABELS: Record<SuiteProductId, string> = {
  biz: "FINDER",
  radar: "RADAR",
  channel: "CHANNEL",
  sentinel: "SENTINEL",
  flood: "FLOOD",
  power: "POWER",
  map: "MAP",
};

export function suiteDomainStrip(): string {
  return SUITE_PRODUCTS.map((p) => p.domain.replace(/^www\./, "")).join(" · ");
}

/** UI strip: product names only (preferred over host/subdomain labels). */
export function suiteProductNameStrip(): string {
  return SUITE_PRODUCTS.map((p) => SUITE_PRODUCT_LABELS[p.id]).join(" · ");
}

export function getProduct(id: SuiteProductId): SuiteProduct {
  const found = SUITE_PRODUCTS.find((p) => p.id === id);
  if (!found) throw new Error(`Unknown suite product: ${id}`);
  return found;
}
