import type { Lead } from './lead'

/** Página de resultados de /api/leads (paginación por limit/offset). */
export interface LeadSearchPage {
  items: Lead[]    // los leads de esta página
  total: number    // total de resultados con los filtros aplicados
  limit: number    // tamaño de página pedido
  offset: number   // desplazamiento pedido
  page: number     // página actual calculada por el backend
  pages: number    // total de páginas
}
