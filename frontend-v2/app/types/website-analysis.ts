/** Historial del dominio en Internet Archive (Wayback Machine). */
export interface WaybackInfo {
  domain: string                        // dominio consultado
  first_seen: string | null             // primera captura conocida
  last_seen: string | null              // última captura
  snapshot_count: number                // nº de capturas archivadas
  age_years: number | null              // antigüedad estimada del sitio
  timeline_url: string                  // link a la línea de tiempo completa
  first_snapshot_url: string | null     // link a la captura más antigua
  last_snapshot_url: string | null      // link a la más reciente
  available: boolean                    // ¿hay capturas para este dominio?
}

/** Un resultado de la búsqueda DuckDuckGo del sitio del negocio. */
export interface WebsiteSearchResult {
  title: string                    // título del resultado
  url: string                      // URL candidata
  snippet: string                  // extracto del resultado
  wayback?: WaybackInfo | null     // info de archive.org si ya se consultó
}

/** Un análisis de sitio web hecho con Playwright (auditoría técnica/SEO). */
export interface WebsiteAnalysis {
  id: number
  lead_id: number                       // a qué lead pertenece
  url: string                           // URL analizada
  final_url: string | null              // URL final tras redirects
  page_title: string | null             // <title> de la página
  last_modified: string | null          // header Last-Modified (si existe)
  load_time_ms: number | null           // tiempo de carga medido
  dom_content_loaded_ms: number | null  // DOMContentLoaded medido
  technologies: string[]                // stack detectado (WordPress, React…)
  seo_title: string | null              // metadatos SEO extraídos
  seo_meta_description: string | null
  seo_h1: string | null
  seo_issues: string[]                  // problemas SEO encontrados
  summary: string | null                // resumen legible del análisis
  metrics: Record<string, unknown>      // métricas extra (incluye wayback)
  status: string                        // completed | failed | …
  error_message: string | null          // detalle si falló
  created_at: string
}

/** Estado global del analizador: solo un Playwright a la vez. */
export interface AnalysisStatus {
  busy: boolean              // ¿hay un análisis corriendo ahora?
  lead_id: number | null     // de qué lead
  url: string | null         // qué URL está analizando
}
