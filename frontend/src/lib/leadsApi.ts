/**
 * Leads + website-research endpoints — thin wrappers over `apiFetch`.
 * Keeps HTTP paths/verbs in one place for dashboard + research panel.
 */
import { apiFetch, apiJson, parseApiError } from "./api";
import type { LeadSearchPage } from "../types/lead-search";
import type {
  AnalysisStatus,
  WaybackInfo,
  WebsiteAnalysis,
  WebsiteSearchResult,
} from "../types/website-analysis";

export type LeadStats = {
  total: number;
  qualified: number;
  small_business: number;
  sells_alcohol: number;
};

export async function fetchLeadStats(): Promise<LeadStats> {
  return apiJson<LeadStats>("/api/leads/stats");
}

export async function searchLeads(params: URLSearchParams): Promise<LeadSearchPage> {
  return apiJson<LeadSearchPage>(`/api/leads?${params.toString()}`);
}

export async function exportLeadsCsv(params: URLSearchParams): Promise<Blob> {
  const response = await apiFetch(`/api/leads/export/csv?${params.toString()}`);
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return response.blob();
}

export async function fetchResearchStatus(): Promise<AnalysisStatus> {
  return apiJson<AnalysisStatus>("/api/leads/website-research/status");
}

export async function fetchWebsiteAnalyses(leadId: number): Promise<WebsiteAnalysis[]> {
  return apiJson<WebsiteAnalysis[]>(`/api/leads/${leadId}/website-analyses`);
}

export async function searchLeadWebsite(
  leadId: number,
  body: { max_results?: number } = { max_results: 8 },
): Promise<{ query: string; results: WebsiteSearchResult[] }> {
  return apiJson(`/api/leads/${leadId}/website-search`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchWayback(url: string): Promise<WaybackInfo> {
  return apiJson(`/api/leads/website-wayback?url=${encodeURIComponent(url)}`);
}

export async function saveLeadWebsiteUrl(
  leadId: number,
  body: { url: string },
): Promise<unknown> {
  return apiJson(`/api/leads/${leadId}/website-url`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function analyzeLeadWebsite(
  leadId: number,
  body: { url: string; save_to_lead?: boolean },
): Promise<WebsiteAnalysis> {
  const response = await apiFetch(`/api/leads/${leadId}/website-analyze`, {
    method: "POST",
    body: JSON.stringify({ save_to_lead: true, ...body }),
  });
  if (response.status === 409) {
    const err = new Error("CONFLICT_BUSY");
    throw err;
  }
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return (await response.json()) as WebsiteAnalysis;
}

export async function fetchAnalysisReportHtml(
  leadId: number,
  analysisId: number,
): Promise<string> {
  const response = await apiFetch(
    `/api/leads/${leadId}/website-analyses/${analysisId}/report`,
  );
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return response.text();
}
