/**
 * Endpoints de leads + website-research — envoltorios finos sobre useApi().
 * Mantiene rutas y verbos HTTP en un solo sitio para el dashboard y el panel
 * de investigación (equivale a lib/leadsApi.ts de la v1).
 */
import type { LeadSearchPage } from '~/types/lead-search'
import type {
  AnalysisStatus,
  WaybackInfo,
  WebsiteAnalysis,
  WebsiteSearchResult,
} from '~/types/website-analysis'

export type LeadStats = {
  total: number
  qualified: number
  small_business: number
  sells_alcohol: number
}

export function useLeadsApi() {
  const { apiFetch, apiJson, parseApiError } = useApi()

  return {
    fetchLeadStats(): Promise<LeadStats> {
      return apiJson<LeadStats>('/api/leads/stats')
    },

    searchLeads(params: URLSearchParams): Promise<LeadSearchPage> {
      return apiJson<LeadSearchPage>(`/api/leads?${params.toString()}`)
    },

    async exportLeadsCsv(params: URLSearchParams): Promise<Blob> {
      const response = await apiFetch(`/api/leads/export/csv?${params.toString()}`)
      if (!response.ok) {
        throw new Error(await parseApiError(response))
      }
      return response.blob()
    },

    fetchResearchStatus(): Promise<AnalysisStatus> {
      return apiJson<AnalysisStatus>('/api/leads/website-research/status')
    },

    fetchWebsiteAnalyses(leadId: number): Promise<WebsiteAnalysis[]> {
      return apiJson<WebsiteAnalysis[]>(`/api/leads/${leadId}/website-analyses`)
    },

    searchLeadWebsite(
      leadId: number,
      body: { max_results?: number } = { max_results: 8 },
    ): Promise<{ query: string; results: WebsiteSearchResult[] }> {
      return apiJson(`/api/leads/${leadId}/website-search`, {
        method: 'POST',
        body: JSON.stringify(body),
      })
    },

    fetchWayback(url: string): Promise<WaybackInfo> {
      return apiJson<WaybackInfo>(`/api/leads/website-wayback?url=${encodeURIComponent(url)}`)
    },

    saveLeadWebsiteUrl(leadId: number, body: { url: string }): Promise<unknown> {
      return apiJson(`/api/leads/${leadId}/website-url`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      })
    },

    async analyzeLeadWebsite(
      leadId: number,
      body: { url: string; save_to_lead?: boolean },
    ): Promise<WebsiteAnalysis> {
      const response = await apiFetch(`/api/leads/${leadId}/website-analyze`, {
        method: 'POST',
        body: JSON.stringify({ save_to_lead: true, ...body }),
      })
      // 409 = ya hay un análisis corriendo; el panel lo trata distinto al resto
      if (response.status === 409) {
        throw new Error('CONFLICT_BUSY')
      }
      if (!response.ok) {
        throw new Error(await parseApiError(response))
      }
      return (await response.json()) as WebsiteAnalysis
    },

    async fetchAnalysisReportHtml(leadId: number, analysisId: number): Promise<string> {
      const response = await apiFetch(`/api/leads/${leadId}/website-analyses/${analysisId}/report`)
      if (!response.ok) {
        throw new Error(await parseApiError(response))
      }
      return response.text()
    },
  }
}
