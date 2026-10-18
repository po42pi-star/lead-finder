// Типы повторяют Pydantic-схемы бэкенда (core/*/schemas.py)

export interface CheckboxItem {
  id: string;
  label: string;
}

export interface CheckboxGroup {
  id: string;
  title: string;
  items: CheckboxItem[];
}

export interface ExtraFieldMeta {
  id: keyof ExtraFields;
  label: string;
  hint: string;
  placeholder: string;
}

export interface Option {
  id: string;
  label: string;
}

export interface FiltersMeta {
  checkbox_groups: CheckboxGroup[];
  extra_fields: ExtraFieldMeta[];
  sort_options: Option[];
  group_options: Option[];
}

export interface ExtraFields {
  geography: string;
  keywords: string;
  adjacent_industries: string;
  exclude_keywords: string;
  min_turnover_mln: string;
  activity_period: string;
  project_types: string;
  technical_requirements: string;
  contact_channels: string;
  search_comment: string;
}

export interface SearchFilters {
  checkboxes: string[];
  extra: ExtraFields;
}

export type SortOption = "score_desc" | "name_asc" | "region_asc" | "updated_desc";
export type GroupOption = "none" | "segment" | "region";

export interface ScoreBreakdownItem {
  delta: number;
  reason: string;
  matched: boolean;
}

export interface Lead {
  lead_id: string;
  company_name: string;
  inn?: string | null;
  segment: string;
  region?: string | null;
  score: number;
  score_breakdown: ScoreBreakdownItem[];
  turnover_mln?: number | null;
  employees?: number | null;
  website?: string | null;
  contact_name?: string | null;
  contact_phone?: string | null;
  contact_email?: string | null;
  source: string;
  updated_at?: string | null;
}

export interface LeadGroup {
  key: string;
  title: string;
  leads: Lead[];
}

export interface SearchResponse {
  session_id: string;
  leads: Lead[];
  groups?: LeadGroup[] | null;
  shown_count: number;
  total_count: number;
  has_more: boolean;
}

export type Confidence = "ok" | "warning" | "error";

export interface AnalyticsItem {
  text: string;
  confidence: Confidence;
  source?: string | null;
}

export interface AnalyticsBlock {
  title: string;
  items: AnalyticsItem[];
  summary?: string | null;
}

export interface RecommendedQuestion {
  question_id: string;
  text: string;
  source: string;
  methodology_tag?: string | null;
  category?: string | null;
  used_in_call?: string | null;
}

export interface AnalyticsReport {
  report_id: string;
  lead_id: string;
  company_name: string;
  segment: string;
  score: number;
  region?: string | null;
  mandatory: Record<string, AnalyticsBlock>;
  optional: Record<string, AnalyticsBlock | RecommendedQuestion[] | unknown>;
  question_set_id?: string | null;
  questions: RecommendedQuestion[];
  created_at: string;
}

export type ChatMode = "search" | "help";

export interface ChatContext {
  lead_id?: string;
  segment?: string;
  score?: number;
  company_name?: string;
  page?: string;
}

export interface ChatSource {
  doc_id: string;
  section: string;
  score: number;
}

export interface ChatResponse {
  session_id: string;
  interaction_id: string;
  answer: string;
  sources: ChatSource[];
  cache_hit: boolean;
  fallback_used: boolean;
  suggested_followups: string[];
}
