import { useState } from "react";
import { Field } from "../components/ui";
import { api } from "../lib/api";
import { store } from "../lib/store";
import type { Connection } from "../lib/types";

/**
 * Sign-in screen.
 *
 * Two paths, one destination (a saved Connection): email + password is the
 * everyday path for a teammate (backend mints a session token, see
 * app/db/sessions.py); the API key path stays as a fallback for whoever is
 * setting the deployment up in the first place, before any logins exist.
 */
export function Connect({
  onConnected,
  onCancel,
}: {
  onConnected: (conn: Connection) => void;
  onCancel?: () => void;
}) {
  const [mode, setMode] = useState<"signin" | "apikey">("signin");
  const [baseUrl, setBaseUrl] = useState("http://127.0.0.1:8100");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function friendlyError(err: unknown): string {
    if (err instanceof Error) {
      return err.message === "Failed to fetch"
        ? "Can't reach the API. Is the backend running on that address?"
        : err.message;
    }
    return String(err);
  }

  async function signIn() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(baseUrl.trim().replace(/\/$/, "") + "/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail ?? "Sign-in failed.");
      const saved = store.save({
        label: body.tenant_name ?? "MIDAS",
        apiKey: body.session_token,
        baseUrl: baseUrl.trim(),
      });
      store.setActive(saved.id);
      onConnected(saved);
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      setBusy(false);
    }
  }

  async function connectWithKey() {
    setBusy(true);
    setError(null);
    const candidate: Connection = {
      id: crypto.randomUUID(),
      label: "…",
      apiKey: apiKey.trim(),
      baseUrl: baseUrl.trim(),
      color: "#C8283C",
    };
    try {
      const tenant = await api.me(candidate);
      const saved = store.save({ label: tenant.name, apiKey: candidate.apiKey, baseUrl: candidate.baseUrl });
      store.setActive(saved.id);
      onConnected(saved);
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      setBusy(false);
    }
  }

  const canSubmit = mode === "signin" ? !!email.trim() && !!password : !!apiKey.trim();

  return (
    <div className="setup">
      <div className="setup-card">
        <div className="brand-lockup">
          <img src="/brand/cmart-mark.svg" alt="CMART Solutions" className="brand-logo" />
          <div className="brand-lockup-text">
            <div className="brand-name">MIDAS</div>
            <div className="brand-acronym">
              Marketing Intelligence &amp; Decision Automation System
            </div>
            <div className="brand-by">by CMART Solutions Pvt Ltd</div>
          </div>
        </div>

        <p className="muted" style={{ fontSize: 13, marginTop: 18, lineHeight: 1.65 }}>
          {mode === "signin"
            ? "Sign in with your CMART email to open the console."
            : "Connect with a tenant API key — shown once when this deployment was set up."}
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

          {mode === "signin" ? (
            <>
              <Field label="Email">
                <input
                  className="input"
                  type="email"
                  value={email}
                  placeholder="you@cmartsolutions.com"
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && canSubmit && signIn()}
                />
              </Field>
              <Field label="Password">
                <input
                  className="input"
                  type="password"
                  value={password}
                  placeholder="••••••••"
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && canSubmit && signIn()}
                />
              </Field>
            </>
          ) : (
            <Field label="Tenant API key" hint="Shown once when the tenant was provisioned.">
              <input
                className="input mono"
                value={apiKey}
                placeholder="bx_live_…"
                onChange={(e) => setApiKey(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && canSubmit && connectWithKey()}
              />
            </Field>
          )}
        </div>

        <div className="row" style={{ marginTop: 8 }}>
          <button
            className="btn primary"
            onClick={mode === "signin" ? signIn : connectWithKey}
            disabled={busy || !canSubmit}
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
          {onCancel && (
            <button className="btn ghost" onClick={onCancel}>Cancel</button>
          )}
        </div>

        <button
          className="link-btn"
          style={{ marginTop: 16 }}
          onClick={() => {
            setMode(mode === "signin" ? "apikey" : "signin");
            setError(null);
          }}
        >
          {mode === "signin" ? "Have a tenant API key instead?" : "Sign in with email instead"}
        </button>
      </div>
    </div>
  );
}
