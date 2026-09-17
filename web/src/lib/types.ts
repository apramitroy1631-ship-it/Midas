export type Autonomy = "autonomous" | "review_required";

export interface TenantPolicy {
  autonomy: Autonomy;
  auto_publish: boolean;
  max_revision_cycles: number;
  forbidden_claims: string[];
  required_disclaimers: string[];
  banned_phrases: string[];
}

export interface AutopilotConfig {
  enabled: boolean;
  interval_minutes: number;
  brand_id: string | null;
  last_run_at: string | null;
  next_run_at: string | null;
  due_now?: boolean;
  quota_block?: string | null;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  status: string;
  api_key_prefix: string;
  policy: TenantPolicy;
  autopilot: AutopilotConfig;
  limits: { monthly_run_quota: number; monthly_budget_usd: number };
  usage: { runs_this_period: number; spend_usd: number; period: string };
  model_overrides: Record<string, unknown>;
  created_at: string;
}

export interface Brand {
  id: string;
  name: string;
  description: string;
  industry: string;
  tone: string;
  usp: string;
  target_audience: string;
  website: string;
  memory: {
    past_campaigns?: string[];
    latest_insights?: string[];
    winning_angles?: string[];
    exhausted_angles?: string[];
    brand_guidelines?: {
      visual_style?: string;
      preferred_channels?: string[];
      content_restrictions?: string[];
    };
  };
  created_at: string;
}

export interface RunSummary {
  id: string;
  brand_id: string;
  brand_name: string;
  status: string;
  goal: string;
  goal_origin: string;
  trigger: string;
  revisions: number;
  qa_passed: boolean | null;
  brand_safety_score: number | null;
  goal_alignment_score: number | null;
  asset_count: number;
  duration_ms: number;
  created_at: string;
}

export interface RunDetail extends RunSummary {
  plan?: Record<string, any> | null;
  research?: Record<string, any> | null;
  strategy?: Record<string, any> | null;
  content?: Record<string, any> | null;
  seo?: Record<string, any> | null;
  qa_report?: Record<string, any> | null;
  analytics?: Record<string, any> | null;
  learning?: Record<string, any> | null;
  usage?: Record<string, any> | null;
  dropped_channels?: string[];
  events?: StepEvent[];
  error?: string | null;
}

export interface Asset {
  id: string;
  run_id: string;
  brand_id: string;
  brand_name: string;
  channel: string;
  headline: string;
  body: string;
  call_to_action: string;
  status: string;
  goal: string;
  seo?: {
    primary_keyword?: string;
    secondary_keywords?: string[];
    meta_title?: string;
    meta_description?: string;
    slug?: string;
    hashtags?: string[];
  } | null;
  created_at: string;
}

export interface AuditEntry {
  id: string;
  run_id: string;
  brand_id: string;
  action: string;
  actor: string;
  trigger: string;
  detail: Record<string, any>;
  created_at: string;
}

export interface Stats {
  total_runs: number;
  published_runs: number;
  abandoned_runs: number;
  failed_runs: number;
  total_assets: number;
  self_directed_runs: number;
  avg_goal_alignment: number | null;
  avg_brand_safety: number | null;
  avg_revisions: number;
  llm_spend_usd: number;
}

export interface StepEvent {
  node: string;
  label: string;
  status: string;
  revision: number;
  output: any;
  at: string;
  elapsed_ms: number;
}

/** A saved connection to one tenant. Keys live only in this browser. */
export interface Connection {
  id: string;
  label: string;
  apiKey: string;
  baseUrl: string;
  color: string;
  /** Only set when connected via email/password sign-in, not the raw API key fallback. */
  userEmail?: string;
}
