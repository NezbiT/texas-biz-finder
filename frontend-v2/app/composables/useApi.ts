/**
 * Cliente HTTP compartido de TxBizFinder (equivale a lib/api.ts de la v1).
 *
 * Cambio vs la v1: allí `env` era una constante de módulo leída de import.meta.env.
 * En Nuxt la config pública vive en runtimeConfig y solo se puede leer dentro del
 * ciclo de la app, así que esto es un composable en vez de un módulo suelto.
 */
export type ApiFetchOptions = RequestInit & {
  /** Omite la cabecera X-API-Key (endpoints públicos). */
  public?: boolean
  /** Por defecto true — pone Content-Type JSON cuando el body es string. */
  json?: boolean
}

/** Extrae el mensaje de error del cuerpo de una respuesta fallida. */
export async function parseApiError(response: Response): Promise<string> {
  const body = await response.json().catch(() => null)
  if (typeof body?.detail === 'string') return body.detail
  if (body?.detail?.message) return String(body.detail.message)
  if (Array.isArray(body?.detail)) {
    const parts = body.detail
      .map((item: { msg?: string } | string) =>
        typeof item === 'string' ? item : item?.msg || JSON.stringify(item),
      )
      .filter(Boolean)
    if (parts.length) return parts.join('; ')
  }
  if (response.status === 503) {
    return 'API temporarily unavailable — check /health (data backend or research disabled).'
  }
  return `API error ${response.status}`
}

export function useApi() {
  const config = useRuntimeConfig()
  const apiKey = config.public.adminApiKey
  // Sin barra final, para que los joins de ruta queden limpios
  const baseUrl = String(config.public.apiBaseUrl || '').replace(/\/+$/, '')

  /** URL absoluta o de mismo origen para una ruta de API (`/api/...`). */
  function apiUrl(path: string): string {
    const normalized = path.startsWith('/') ? path : `/${path}`
    return baseUrl ? `${baseUrl}${normalized}` : normalized
  }

  function authHeaders(extra?: HeadersInit): Headers {
    const headers = new Headers(extra)
    if (!headers.has('X-API-Key')) {
      headers.set('X-API-Key', apiKey)
    }
    return headers
  }

  /** fetch con base URL, API key y errores consistentes. */
  async function apiFetch(path: string, init: ApiFetchOptions = {}): Promise<Response> {
    const { public: isPublic, json, headers: initHeaders, ...rest } = init
    const headers = isPublic ? new Headers(initHeaders) : authHeaders(initHeaders)

    if (json !== false && rest.body && typeof rest.body === 'string' && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }

    return fetch(apiUrl(path), { ...rest, headers })
  }

  async function apiJson<T>(path: string, init?: ApiFetchOptions): Promise<T> {
    const response = await apiFetch(path, init)
    if (!response.ok) {
      throw new Error(await parseApiError(response))
    }
    return (await response.json()) as T
  }

  return { apiKey, apiUrl, authHeaders, apiFetch, apiJson, parseApiError }
}
