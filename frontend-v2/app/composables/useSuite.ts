/**
 * Productos de la suite resueltos contra el entorno.
 *
 * URLs por defecto = paths en un solo dominio:
 *   https://www.txbizfinder.com/radar  (no radar.txbizfinder.com)
 */
import {
  STAR_TIP_ORDER,
  SUITE_PATHS,
  SUITE_PRODUCT_STYLES,
  SUITE_PUBLIC_ORIGIN,
  suitePathLabel,
  suitePublicUrl,
  type SuiteProduct,
  type SuiteProductId,
} from '~/config/suite'

type SuiteEnv = {
  wwwUrl: string
  bizAppPath: string
  radarUrl: string
  channelUrl: string
  sentinelUrl: string
  floodUrl: string
  powerUrl: string
  mapUrl: string
}

function stripSlash(url: string): string {
  return url.replace(/\/+$/, '')
}

function apexHost(host: string): string {
  return host.replace(/^www\./, '')
}

/** Otros productos bajo el mismo apex (path routing). */
function isSuiteSiblingHref(href: string, wwwOrigin: string): boolean {
  const siblingRoots = new Set(['radar', 'channel', 'sentinel', 'flood', 'power', 'map'])

  if (href.startsWith('/') && !href.startsWith('//')) {
    const first = href.split('/').filter(Boolean)[0] || ''
    return siblingRoots.has(first)
  }

  if (href.startsWith('http://') || href.startsWith('https://')) {
    try {
      const u = new URL(href)
      const base = new URL(wwwOrigin)
      if (apexHost(u.host) !== apexHost(base.host)) return false
      const first = u.pathname.split('/').filter(Boolean)[0] || ''
      return siblingRoots.has(first)
    } catch {
      return false
    }
  }
  return false
}

function displayLabel(href: string, pathFallback: string): string {
  if (href.startsWith('/') && !href.startsWith('//')) {
    return suitePathLabel(href)
  }
  if (href.startsWith('http://') || href.startsWith('https://')) {
    try {
      const u = new URL(href)
      const path = u.pathname === '/' ? '' : u.pathname.replace(/\/+$/, '')
      return `${apexHost(u.host)}${path}`
    } catch {
      return pathFallback
    }
  }
  return pathFallback
}

export function useSuite() {
  const raw = useRuntimeConfig().public.suite as SuiteEnv
  const wwwUrl = stripSlash(raw.wwwUrl || SUITE_PUBLIC_ORIGIN)

  const bizAppPath = computed(() => {
    const p = raw.bizAppPath || SUITE_PATHS.biz
    return p.startsWith('/') ? p : `/${p}`
  })

  const products = computed<readonly SuiteProduct[]>(() => {
    const defaults = {
      radar: suitePublicUrl(SUITE_PATHS.radar),
      channel: suitePublicUrl(SUITE_PATHS.channel),
      sentinel: suitePublicUrl(SUITE_PATHS.sentinel),
      flood: suitePublicUrl(SUITE_PATHS.flood),
      power: suitePublicUrl(SUITE_PATHS.power),
      map: suitePublicUrl(SUITE_PATHS.map),
    }

    const entries: ReadonlyArray<[SuiteProductId, string, string]> = [
      ['biz', bizAppPath.value, suitePathLabel(bizAppPath.value)],
      ['radar', stripSlash(raw.radarUrl || defaults.radar), suitePathLabel(SUITE_PATHS.radar)],
      ['channel', stripSlash(raw.channelUrl || defaults.channel), suitePathLabel(SUITE_PATHS.channel)],
      ['sentinel', stripSlash(raw.sentinelUrl || defaults.sentinel), suitePathLabel(SUITE_PATHS.sentinel)],
      ['flood', stripSlash(raw.floodUrl || defaults.flood), suitePathLabel(SUITE_PATHS.flood)],
      ['power', stripSlash(raw.powerUrl || defaults.power), suitePathLabel(SUITE_PATHS.power)],
      ['map', stripSlash(raw.mapUrl || defaults.map), suitePathLabel(SUITE_PATHS.map)],
    ]

    return entries.map(([id, href, fallbackLabel]) => {
      const isBiz = id === 'biz'
      const sameOrigin = isBiz || isSuiteSiblingHref(href, wwwUrl)
      return {
        id,
        href,
        // Solo /app es SPA interna; el resto hace full page load
        external: !isBiz,
        sameOrigin,
        domain: displayLabel(href, fallbackLabel),
        nameKey: `product${capitalize(id)}Name`,
        blurbKey: `product${capitalize(id)}Blurb`,
        ctaKey: `product${capitalize(id)}Cta`,
        ...SUITE_PRODUCT_STYLES[id],
      }
    })
  })

  const starTipProducts = computed(() => STAR_TIP_ORDER.map((id) => getProduct(id)))

  function getProduct(id: SuiteProductId): SuiteProduct {
    const found = products.value.find((p) => p.id === id)
    if (!found) throw new Error(`Unknown suite product: ${id}`)
    return found
  }

  function suiteDomainStrip(): string {
    return products.value.map((p) => p.domain).join(' · ')
  }

  return { products, starTipProducts, bizAppPath, getProduct, suiteDomainStrip }
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}
