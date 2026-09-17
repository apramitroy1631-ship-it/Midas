import type {
  Asset,
  AuditEntry,
  AutopilotConfig,
  Brand,
  Connection,
  RunDetail,
  RunSummary,
  Stats,
  Tenant,
} from "./types";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function request<T>(
  conn: Connection,
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetch(conn.baseUrl.replace(/\/$/, "") + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": conn.apiKey,
      ...(init.headers || {}),
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error body — keep the status text */
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  me: (c: Connection) => request<Tenant>(c, "/v1/me"),
  updateMe: (c: Connection, body: unknown) =>
    request<Tenant>(c, "/v1/me", { method: "PATCH", body: JSON.stringify(body) }),

  brands: (c: Connection) => request<Brand[]>(c, "/v1/brands"),
  brand: (c: Connection, id: string) => request<Brand>(c, `/v1/brands/${id}`),
  createBrand: (c: Connection, body: unknown) =>
    request<Brand>(c, "/v1/brands", { method: "POST", body: JSON.stringify(body) }),
  updateBrand: (c: Connection, id: string, body: unknown) =>
    request<Brand>(c, `/v1/brands/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteBrand: (c: Connection, id: string) =>
    request<void>(c, `/v1/brands/${id}`, { method: "DELETE" }),

  runs: (c: Connection, brandId?: string) =>
    request<RunSummary[]>(c, "/v1/runs" + (brandId ? `?brand_id=${brandId}` : "")),
  run: (c: Connection, id: string) => request<RunDetail>(c, `/v1/runs/${id}`),

  assets: (c: Connection, brandId?: string) =>
    request<Asset[]>(c, "/v1/assets" + (brandId ? `?brand_id=${brandId}` : "")),
  updateAsset: (c: Connection, id: string, body: unknown) =>
    request<Asset>(c, `/v1/assets/${id}`, { method: "PATCH", body: JSON.stringify(body) }),

  audit: (c: Connection) => request<AuditEntry[]>(c, "/v1/audit"),
  stats: (c: Connection) => request<Stats>(c, "/v1/stats"),

  autopilot: (c: Connection) => request<AutopilotConfig>(c, "/v1/autopilot"),
  autopilotTick: (c: Connection) =>
    request<{ skipped: boolean; reason?: string; run_id?: string; status?: string }>(
      c,
      "/v1/autopilot/tick",
      { method: "POST" }
    ),

  health: (baseUrl: string) =>
    fetch(baseUrl.replace(/\/$/, "") + "/health").then((r) => r.json()),
};

/**
 * Streams a run.
 *
 * The browser's EventSource can't POST, so the fetch body is parsed as SSE by
 * hand: events are separated by a blank line, and a chunk may arrive split
 * across reads, which is why the tail is carried over in `buffer`.
 */
export async function streamRun(
  conn: Connection,
  body: unknown,
  onEvent: (event: string, data: any) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(conn.baseUrl.replace(/\/$/, "") + "/v1/runs/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": conn.apiKey },
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok || !res.body) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* keep the status line */
    }
    throw new ApiError(detail, res.status);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    // sse-starlette separates fields and events with CRLF, so normalise before
    // splitting — a "\n\n" split never matches "\r\n\r\n" and silently swallows
    // every event.
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      let event = "message";
      const dataLines: string[] = [];
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (!dataLines.length) continue;
      const raw = dataLines.join("\n");
      try {
        onEvent(event, JSON.parse(raw));
      } catch {
        onEvent(event, raw);
      }
    }
  }
}
