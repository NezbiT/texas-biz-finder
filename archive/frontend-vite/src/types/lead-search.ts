import type { Lead } from "./lead";

export interface LeadSearchPage {
  items: Lead[];
  total: number;
  limit: number;
  offset: number;
  page: number;
  pages: number;
}