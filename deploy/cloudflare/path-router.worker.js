/**
 * TxBizFinder Intelligence — path router (Cloudflare Worker)
 *
 * Single domain, path-based products. NO tunnel to a home PC.
 *
 * CURRENT MODE: stripPrefix=true for product UIs so existing Vercel deploys
 * (root-mounted Nuxt apps) work at www.txbizfinder.com/{radar,channel,…}.
 *
 * After each product is redeployed with app.baseURL=/radar/ etc., set
 * stripPrefix:false for that product so /radar/_nuxt assets resolve.
 *
 *   / , /app        → Finder UI (Vercel) — path kept (SPA/Nuxt handles routes)
 *   /api/* , /health → FastAPI (Oracle API_ORIGIN)
 *   /radar/*        → PermitRadar (prefix stripped until baseURL deploy)
 *   /channel/*      → ChannelWatch
 *   /sentinel/*     → Emissions Sentinel UI
 *   /flood/*        → FloodGuard
 *   /power/*        → PowerPulse
 *   /map/*          → MapHub
 */

const DEFAULTS = {
  FINDER_ORIGIN: 'https://txbizfinder-web.vercel.app',
  RADAR_ORIGIN: 'https://permitradar-houston.vercel.app',
  CHANNEL_ORIGIN: 'https://channelwatch-laporte.vercel.app',
  SENTINEL_ORIGIN: 'https://emissions-sentinel-web.vercel.app',
  FLOOD_ORIGIN: 'https://floodguard-texas.vercel.app',
  POWER_ORIGIN: 'https://powerpulse-texas.vercel.app',
  MAP_ORIGIN: 'https://maphub-texas.vercel.app',
  API_ORIGIN: '',
}

/**
 * @param {string} pathname
 * @param {Record<string, string>} env
 */
function resolveRoute(pathname, env) {
  const apiOrigin = (env.API_ORIGIN || DEFAULTS.API_ORIGIN || '').replace(/\/$/, '')
  const finder = (env.FINDER_ORIGIN || DEFAULTS.FINDER_ORIGIN).replace(/\/$/, '')

  /** @type {Array<{ prefix: string, origin: string, stripPrefix: boolean, requireOrigin?: boolean }>} */
  const table = [
    { prefix: '/api', origin: apiOrigin, stripPrefix: false, requireOrigin: true },
    { prefix: '/health', origin: apiOrigin, stripPrefix: false, requireOrigin: true },
    // stripPrefix true until those Vercel projects ship baseURL builds
    { prefix: '/radar', origin: (env.RADAR_ORIGIN || DEFAULTS.RADAR_ORIGIN).replace(/\/$/, ''), stripPrefix: true },
    { prefix: '/channel', origin: (env.CHANNEL_ORIGIN || DEFAULTS.CHANNEL_ORIGIN).replace(/\/$/, ''), stripPrefix: true },
    { prefix: '/sentinel', origin: (env.SENTINEL_ORIGIN || DEFAULTS.SENTINEL_ORIGIN).replace(/\/$/, ''), stripPrefix: true },
    { prefix: '/flood', origin: (env.FLOOD_ORIGIN || DEFAULTS.FLOOD_ORIGIN).replace(/\/$/, ''), stripPrefix: true },
    { prefix: '/power', origin: (env.POWER_ORIGIN || DEFAULTS.POWER_ORIGIN).replace(/\/$/, ''), stripPrefix: true },
    { prefix: '/map', origin: (env.MAP_ORIGIN || DEFAULTS.MAP_ORIGIN).replace(/\/$/, ''), stripPrefix: true },
  ]

  for (const row of table) {
    if (pathname === row.prefix || pathname.startsWith(row.prefix + '/')) {
      return row
    }
  }
  return { prefix: '', origin: finder, stripPrefix: false, requireOrigin: false }
}

/**
 * @param {string} requestUrl
 * @param {{ origin: string, prefix: string, stripPrefix: boolean }} route
 */
function buildUpstreamUrl(requestUrl, route) {
  const u = new URL(requestUrl)
  let path = u.pathname
  if (route.stripPrefix && route.prefix) {
    path = path.slice(route.prefix.length) || '/'
    if (!path.startsWith('/')) path = '/' + path
  }
  return new URL(path + u.search, route.origin + '/')
}

export default {
  /**
   * @param {Request} request
   * @param {Record<string, string>} env
   */
  async fetch(request, env) {
    const url = new URL(request.url)
    const route = resolveRoute(url.pathname, env || {})

    if (route.requireOrigin && !route.origin) {
      return new Response(
        JSON.stringify({
          status: 'error',
          detail:
            'API_ORIGIN is not configured. Set the Oracle FastAPI HTTPS origin (wrangler secret put API_ORIGIN).',
        }),
        {
          status: 503,
          headers: { 'content-type': 'application/json; charset=utf-8' },
        },
      )
    }

    const upstream = buildUpstreamUrl(request.url, route)
    const headers = new Headers(request.headers)
    try {
      headers.set('Host', new URL(route.origin).host)
    } catch {
      /* keep */
    }
    headers.set('X-Forwarded-Host', url.host)
    headers.set('X-Forwarded-Proto', url.protocol.replace(':', ''))
    if (route.prefix) headers.set('X-TxBiz-Path-Prefix', route.prefix)

    /** @type {RequestInit} */
    const init = {
      method: request.method,
      headers,
      redirect: 'manual',
    }
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      init.body = request.body
      // @ts-expect-error CF streaming
      init.duplex = 'half'
    }

    let response = await fetch(upstream.toString(), init)

    // Finder SPA fallback: /app (and other client routes) may 404 on old Vite deploy
    if (
      response.status === 404 &&
      route.origin === (env.FINDER_ORIGIN || DEFAULTS.FINDER_ORIGIN).replace(/\/$/, '') &&
      !url.pathname.startsWith('/api')
    ) {
      const fallback = new URL('/' + url.search, route.origin + '/')
      response = await fetch(fallback.toString(), { method: 'GET', headers, redirect: 'manual' })
    }

    return new Response(response.body, response)
  },
}
