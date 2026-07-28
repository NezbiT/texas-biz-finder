/**
 * Catálogo de productos de TxBizFinder Intelligence — parte ESTÁTICA.
 *
 * En la v1 este archivo también resolvía las URLs (importaba config/env.ts a
 * nivel de módulo). Aquí no puede: en Nuxt las URLs vienen de runtimeConfig y
 * eso solo se lee dentro del ciclo de la app. Así que lo que depende del
 * entorno vive en `useSuite()` y aquí queda todo lo que es constante.
 */

export type SuiteProductId =
  | 'biz'
  | 'radar'
  | 'channel'
  | 'sentinel'
  | 'flood'
  | 'power'
  | 'map'

/** Clave de traducción. En la v1 era el tipo MessageKey derivado de i18n/en.ts;
 *  aquí los catálogos son JSON, así que se valida contra las locales en runtime. */
export type MessageKey = string

export type SuiteProduct = {
  id: SuiteProductId
  /** Etiqueta visible (p. ej. txbizfinder.com/radar). */
  domain: string
  /** URL absoluta o ruta interna. */
  href: string
  /**
   * true = no es la SPA del finder (full page nav).
   * false = NuxtLink interno (/app).
   */
  external: boolean
  /**
   * true = mismo origen (path en txbizfinder.com) → <a> same-tab.
   * false = dominio externo real → puede abrir en pestaña nueva.
   */
  sameOrigin?: boolean
  nameKey: MessageKey
  blurbKey: MessageKey
  ctaKey: MessageKey
  accent: string
  ring: string
}

/** Presentación fija de cada producto: gradiente y borde al hacer hover. */
export const SUITE_PRODUCT_STYLES: Record<SuiteProductId, { accent: string; ring: string }> = {
  biz: { accent: 'from-orange-500/25 to-orange-500/5', ring: 'hover:border-orange-400/50' },
  radar: { accent: 'from-orange-600/20 to-orange-600/5', ring: 'hover:border-orange-500/50' },
  channel: { accent: 'from-amber-400/20 to-amber-400/5', ring: 'hover:border-amber-400/50' },
  sentinel: { accent: 'from-amber-500/25 to-amber-500/5', ring: 'hover:border-amber-500/50' },
  flood: { accent: 'from-sky-500/25 to-sky-500/5', ring: 'hover:border-sky-400/50' },
  power: { accent: 'from-yellow-500/25 to-yellow-500/5', ring: 'hover:border-yellow-400/50' },
  map: { accent: 'from-orange-400/30 to-amber-500/10', ring: 'hover:border-orange-300/60' },
}

/** Orden en las puntas de la estrella. MAP va en el centro, no en una punta. */
export const STAR_TIP_ORDER: readonly SuiteProductId[] = [
  'flood',
  'biz',
  'radar',
  'channel',
  'sentinel',
  'power',
] as const

export const SUITE_STEPS = [
  { title: 'suiteHowStep1', body: 'suiteHowStep1Body' },
  { title: 'suiteHowStep2', body: 'suiteHowStep2Body' },
  { title: 'suiteHowStep3', body: 'suiteHowStep3Body' },
  { title: 'suiteHowStep4', body: 'suiteHowStep4Body' },
] as const satisfies ReadonlyArray<{ title: MessageKey; body: MessageKey }>

export const SUITE_HOME_PATH = '/'

/**
 * Canonical public base (no trailing slash).
 * All products live as paths: https://www.txbizfinder.com/radar, /flood, …
 * (subdomains + Cloudflare Tunnel to a home PC are retired).
 */
export const SUITE_PUBLIC_ORIGIN = 'https://www.txbizfinder.com'

/**
 * Path map under the single apex domain.
 * Worker / reverse-proxy strips the first segment when forwarding to each app.
 */
export const SUITE_PATHS = {
  home: '/',
  biz: '/app',
  radar: '/radar',
  channel: '/channel',
  sentinel: '/sentinel',
  flood: '/flood',
  power: '/power',
  map: '/map',
  /** FastAPI (Nitro proxy → Oracle). Same origin, no api.* subdomain. */
  api: '/api',
} as const satisfies Record<string, string>

/** Absolute URL helper for suite paths. */
export function suitePublicUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`
  if (p === '/') return SUITE_PUBLIC_ORIGIN
  return `${SUITE_PUBLIC_ORIGIN}${p}`
}

/** Label shown on cards: txbizfinder.com/radar */
export function suitePathLabel(path: string): string {
  const p = path === '/' ? '' : path.startsWith('/') ? path : `/${path}`
  return `txbizfinder.com${p}`
}

/** Crédito de autoría — aparece en los footers de toda la suite. */
export const SUITE_CREATOR = {
  name: 'Mario Alvarez',
  url: 'https://mariosalvarez.com',
  host: 'mariosalvarez.com',
} as const

/** Nombres completos de producto (portales, footer, marquee). */
export const SUITE_PRODUCT_LABELS: Record<SuiteProductId, string> = {
  biz: 'TxBizFinder',
  radar: 'PermitRadar',
  channel: 'ChannelWatch',
  sentinel: 'Emissions Sentinel',
  flood: 'FloodGuard Texas',
  power: 'PowerPulse Texas',
  map: 'Map Hub Texas',
}

/** Etiquetas cortas, solo para las puntas de la estrella de la landing. */
export const STAR_TIP_LABELS: Record<SuiteProductId, string> = {
  biz: 'FINDER',
  radar: 'RADAR',
  channel: 'CHANNEL',
  sentinel: 'SENTINEL',
  flood: 'FLOOD',
  power: 'POWER',
  map: 'MAP',
}

/** Franja de nombres de producto (se prefiere sobre la de hosts). */
export function suiteProductNameStrip(): string {
  return (Object.keys(SUITE_PRODUCT_LABELS) as SuiteProductId[])
    .map((id) => SUITE_PRODUCT_LABELS[id])
    .join(' · ')
}
