const API_BASE = '/api';

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText || 'Request failed');
  return data as T;
}

export const api = {
  health: () => request<{ status: string }>('/health'),

  brands: {
    list: () => request<BrandSummary[]>('/brands'),
    create: (body: BrandCreateBody) =>
      request<BrandResponse>('/brands', { method: 'POST', body: JSON.stringify(body) }),
    get: (id: string) => request<BrandResponse>(`/brands/${id}`),
    update: (id: string, body: Record<string, unknown>) =>
      request<BrandResponse>(`/brands/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
    delete: (id: string) =>
      request<void>(`/brands/${id}`, { method: 'DELETE' }),
  },

  campaigns: {
    list: (brandId: string) =>
      request<Campaign[]>(`/brands/${brandId}/campaigns`),
    get: (brandId: string, campaignId: string) =>
      request<Campaign>(`/brands/${brandId}/campaigns/${campaignId}`),
    create: (brandId: string, body: { goal: string; target_audience: string; budget: number }) =>
      request<CampaignCreateResponse>(`/brands/${brandId}/campaigns/`, {
        method: 'POST',
        body: JSON.stringify({ brand_id: brandId, ...body }),
      }),
    delete: (brandId: string, campaignId: string) =>
      request<void>(`/brands/${brandId}/campaigns/${campaignId}`, { method: 'DELETE' }),
  },
};

export interface BrandGuidelines {
  visual_style: string;
  preferred_channels: string[];
  content_restrictions: string[];
}

export interface BrandCreateBody {
  name: string;
  description: string;
  industry: string;
  tone: string;
  usp: string;
  target_audience: string;
  brand_guidelines?: BrandGuidelines;
  latest_insights?: string[];
}

export interface BrandSummary {
  id: string;
  name: string;
}

export interface BrandResponse {
  id: string;
  name: string;
  description: string;
  industry: string;
  tone: string;
  usp: string;
  target_audience: string;
  memory?: {
    brand_guidelines?: BrandGuidelines;
    latest_insights?: string[];
    past_campaigns?: string[];
  };
  created_at: string;
  updated_at: string;
}

export interface Campaign {
  id: string;
  brand_id: string;
  brand_name?: string;
  status: string;
  goal: string;
  target_audience: string;
  budget: number;
  research?: unknown;
  strategy?: unknown;
  content?: unknown;
  qa_report?: unknown;
  analytics?: unknown;
  created_at?: string;
  updated_at?: string;
}

export interface CampaignCreateResponse {
  id: string;
  status: string;
  research?: unknown;
}
