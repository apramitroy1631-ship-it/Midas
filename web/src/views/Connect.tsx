import { useState } from "react";
import { Field } from "../components/ui";
import { api } from "../lib/api";
import { store } from "../lib/store";
import type { Connection } from "../lib/types";

/**
 * First-run and add-tenant screen.
 *
 * Verifies the key against /v1/me before saving, so a bad key fails here rather
 * than as a confusing 401 three screens later.
 */
export function Connect({
  onConnected,
  onCancel,
}: {
  onConnected: (conn: Connection) => void;
  onCancel?: () => void;
}) {
  const [baseUrl, setBaseUrl] = useState("http://127.0.0.1:8100");
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function connect() {
    setBusy(true);
    setError(null);
    const candidate: Connection = {
      id: crypto.randomUUID(),
      label: "…",
      apiKey: apiKey.trim(),
      baseUrl: baseUrl.trim(),
      color: "#6ea8fe",
    };
    try {
      const tenant = await api.me(candidate);
      const saved = store.save({ label: tenant.name, apiKey: candidate.apiKey, baseUrl: candidate.baseUrl });
      store.setActive(saved.id);
      onConnected(saved);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message === "Failed to fetch"
            ? "Can't reach the API. Is the backend running on that address?"
            : err.message
          : String(err)
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="setup">
      <div className="setup-card">
        <div className="logo" style={{ padding: "0 0 20px" }}>
          <div className="logo-mark">BX</div>
          <div>
            <div className="logo-text">BuildX Console</div>
            <div className="logo-sub">AUTONOMOUS MARKETING</div>
          </div>
        </div>

        <p className="muted" style={{ fontSize: 13, marginTop: 0, lineHeight: 1.65 }}>
          Connect with a tenant API key. Each key sees only its own tenant's brands, runs, and
          assets — connect several and switch between them from the top bar.
        </p>

        {error && (
          <div className="banner danger" style={{ marginTop: 16 }}>
            <span>✕</span>
            <div>{error}</div>
          </div>
        )}

        <div style={{ marginTop: 18 }}>
          <Field label="API base URL">
            <input className="input mono" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
          </Field>
          <Field label="Tenant API key" hint="Shown once when the tenant was provisioned. Stored in this browser only.">
            <input
              className="input mono"
              value={apiKey}
              placeholder="bx_live_…"
              onChange={(e) => setApiKey(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && apiKey && connect()}
            />
          </Field>
        </div>

        <div className="row" style={{ marginTop: 8 }}>
          <button className="btn primary" onClick={connect} disabled={busy || !apiKey.trim()}>
            {busy ? "Verifying…" : "Connect"}
          </button>
          {onCancel && (
            <button className="btn ghost" onClick={onCancel}>Cancel</button>
          )}
        </div>
      </div>
    </div>
  );
}
