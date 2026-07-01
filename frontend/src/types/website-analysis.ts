export interface WaybackInfo {
  domain: string;
  first_seen: string | null;
  last_seen: string | null;
  snapshot_count: number;
  age_years: number | null;
  timeline_url: string;
  first_snapshot_url: string | null;
  last_snapshot_url: string | null;
  available: boolean;
}

export interface WebsiteSearchResult {
  title: string;
  url: string;
  snippet: string;
  wayback?: WaybackInfo | null;
}

export interface WebsiteSearchResponse {
  query: string;
  results: WebsiteSearchResult[];
}

export interface WebsiteAnalysis {
  id: number;
  lead_id: number;
  url: string;
  final_url: string | null;
  page_title: string | null;
  last_modified: string | null;
  load_time_ms: number | null;
  dom_content_loaded_ms: number | null;
  technologies: string[];
  seo_title: string | null;
  seo_meta_description: string | null;
  seo_h1: string | null;
  seo_issues: string[];
  summary: string | null;
  metrics: Record<string, unknown>;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface AnalysisStatus {
  busy: boolean;
  lead_id: number | null;
  url: string | null;
}