import { useEffect, useMemo, useState } from "react";
import { DateRangePicker } from "../components/DateRangePicker";
import { Badge, Card, Empty, Field, ToggleRow } from "../components/ui";
import { api } from "../lib/api";
import type { AutopilotConfig, Brand, Connection, LogEntry, Tenant } from "../lib/types";

const LEVEL_TONE: Record<string, "ok" | "warn" | "danger" | "info" | "muted"> = {
  DEBUG: "muted",
  INFO: "info",
  WARNING: "warn",
  ERROR: "danger",
  CRITICAL: "danger",
};

function DeveloperLogs({ conn }: { conn: Connection }) {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [levels, setLevels] = useState<string[]>([]);
  const [activeCategories, setActiveCategories] = useState<string[]>([]);
  const [activeLevels, setActiveLevels] = useState<string[]>([]);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleIn(list: string[], setList: (v: string[]) => void, value: string) {
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
  }

  const load = useMemo(
    () => async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.logs(conn, {
          category: activeCategories,
          level: activeLevels,
          since: from ? new Date(from).toISOString() : undefined,
          until: to ? new Date(new Date(to).getTime() + 86_400_000 - 1).toISOString() : undefined,
        });
        setEntries(res.entries);
        setCategories(res.categories);
        setLevels(res.levels);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    },
    [conn, activeCategories, activeLevels, from, to]
  );

  useEffect(() => {
    void load();
  }, [load]);

  const anyFilterActive = !!(activeCategories.length || activeLevels.length || from || to);

  return (
    <Card
      title="Developer logs"
      sub="Live application log stream, most recent first"
      action={
        <button className="btn ghost sm" onClick={() => void load()} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      }
    >
      <div className="row wrap" style={{ marginBottom: 12 }}>
        <DateRangePicker from={from} to={to} onChange={(f, t) => { setFrom(f); setTo(t); }} />
      </div>
      <div className="row wrap" style={{ marginBottom: 12 }}>
        <span className="field-label" style={{ margin: 0, alignSelf: "center" }}>Type</span>
        {levels.map((lv) => (
          <button
            key={lv}
            type="button"
            className={"chip-toggle" + (activeLevels.includes(lv) ? " active" : "")}
            onClick={() => toggleIn(activeLevels, setActiveLevels, lv)}
          >
            {lv}
          </button>
        ))}
        <span className="field-label" style={{ margin: "0 0 0 10px", alignSelf: "center" }}>Category</span>
        {categories.map((c) => (
          <button
            key={c}
            type="button"
            className={"chip-toggle" + (activeCategories.includes(c) ? " active" : "")}
            onClick={() => toggleIn(activeCategories, setActiveCategories, c)}
          >
            {c}
          </button>
        ))}
        <span className="spacer" />
        {anyFilterActive && (
          <button
            className="btn ghost sm"
            onClick={() => { setActiveCategories([]); setActiveLevels([]); setFrom(""); setTo(""); }}
          >
            Clear filters
          </button>
        )}
      </div>

      {error && <div className="banner danger"><span>✕</span><div>{error}</div></div>}

      {!error && entries.length === 0 ? (
        <Empty icon="▤" title={loading ? "Loading…" : "No log entries"} text="Nothing has been logged yet for this filter." />
      ) : (
        <div className="table-wrap" style={{ maxHeight: 420, overflowY: "auto" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Type</th>
                <th>Category</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id} style={{ cursor: "default" }}>
                  <td className="mono dim" style={{ whiteSpace: "nowrap" }}>
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                  <td><Badge tone={LEVEL_TONE[e.level] ?? "muted"}>{e.level}</Badge></td>
                  <td className="mono dim">{e.category}</td>
                  <td className="truncate" style={{ maxWidth: 480 }}>{e.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

export function Settings({
  conn,
  tenant,
  brands,
  autopilot,
  onSaved,
  onDisconnect,
}: {
  conn: Connection;
  tenant: Tenant;
  brands: Brand[];
  autopilot: AutopilotConfig | null;
  onSaved: () => void;
  onDisconnect: () => void;
}) {
  const [policy, setPolicy] = useState(tenant.policy);
  const [ap, setAp] = useState<AutopilotConfig>(
    autopilot ?? tenant.autopilot ?? { enabled: false, interval_minutes: 1440, brand_id: null, last_run_at: null, next_run_at: null }
  );
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setMsg(null);
    try {
      await api.updateMe(conn, {
        policy,
        autopilot: {
          enabled: ap.enabled,
          interval_minutes: Number(ap.interval_minutes) || 1440,
          brand_id: ap.brand_id || null,
          last_run_at: ap.last_run_at,
          next_run_at: ap.next_run_at,
        },
      });
      setMsg("Saved. New runs use these settings immediately.");
      onSaved();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  const lines = (v: string[]) => v.join("\n");
  const parse = (v: string) => v.split("\n").map((s) => s.trim()).filter(Boolean);

  return (
    <div className="content-narrow col">
      {msg && <div className="banner info"><span>ⓘ</span><div>{msg}</div></div>}

      <Card title="Autonomy" sub="How much the agents decide without a person">
        <ToggleRow
          title="Run fully autonomously"
          desc="QA failures loop back to the writer as revision cycles instead of stopping for human approval. Turning this off keeps the identical agent pipeline but parks finished content in a review queue."
          on={policy.autonomy === "autonomous"}
          onChange={(v) => setPolicy({ ...policy, autonomy: v ? "autonomous" : "review_required" })}
        />
        <ToggleRow
          title="Publish on a clean QA pass"
          desc="Assets go straight to the content library the moment QA passes them."
          on={policy.auto_publish}
          onChange={(v) => setPolicy({ ...policy, auto_publish: v })}
        />

        <Field
          label="Revision budget"
          hint="How many times the writer may be sent back before the system arbitrates: assets that individually cleared QA still ship, the rest are dropped. Never blocks waiting on a person."
        >
          <input
            className="input mono"
            type="number"
            min={0}
            max={5}
            value={policy.max_revision_cycles}
            onChange={(e) => setPolicy({ ...policy, max_revision_cycles: Number(e.target.value) })}
          />
        </Field>
      </Card>

      <Card title="Guardrails" sub="Rules QA treats as blocking, on top of what it infers">
        <Field label="Forbidden claims" hint="One per line. Any asset making one of these fails QA outright.">
          <textarea
            className="textarea"
            value={lines(policy.forbidden_claims)}
            onChange={(e) => setPolicy({ ...policy, forbidden_claims: parse(e.target.value) })}
          />
        </Field>
        <Field label="Banned phrases" hint="One per line. Usually filler the brand has decided it never uses.">
          <textarea
            className="textarea"
            value={lines(policy.banned_phrases)}
            onChange={(e) => setPolicy({ ...policy, banned_phrases: parse(e.target.value) })}
          />
        </Field>
        <Field label="Required disclaimers" hint="One per line. Must appear wherever the related claim does.">
          <textarea
            className="textarea"
            value={lines(policy.required_disclaimers)}
            onChange={(e) => setPolicy({ ...policy, required_disclaimers: parse(e.target.value) })}
          />
        </Field>
      </Card>

      <Card title="Autopilot" sub="Campaigns that run with nobody present">
        <ToggleRow
          title="Enable scheduled runs"
          desc="On a schedule, the Campaign Director reads brand memory, picks its own goal, and runs the full pipeline unattended."
          on={ap.enabled}
          onChange={(v) => setAp({ ...ap, enabled: v })}
        />
        <div className="grid grid-2" style={{ marginTop: 14 }}>
          <Field label="Interval (minutes)" hint="1440 = daily.">
            <input
              className="input mono"
              type="number"
              min={5}
              value={ap.interval_minutes}
              onChange={(e) => setAp({ ...ap, interval_minutes: Number(e.target.value) })}
            />
          </Field>
          <Field label="Brand" hint="Leave on rotation and it works the brand idle longest.">
            <select
              className="select"
              value={ap.brand_id ?? ""}
              onChange={(e) => setAp({ ...ap, brand_id: e.target.value || null })}
            >
              <option value="">Rotate across all brands</option>
              {brands.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </Field>
        </div>
        {ap.last_run_at && (
          <div className="mono dim" style={{ fontSize: 11.5 }}>
            last {ap.last_run_at} · next {ap.next_run_at}
          </div>
        )}
      </Card>

      <div className="row">
        <button className="btn primary" onClick={save} disabled={saving}>
          {saving ? "Saving…" : "Save settings"}
        </button>
      </div>

      <Card title="Connection" sub="This browser only">
        <dl className="kv" style={{ fontSize: 12.5 }}>
          <dt>Tenant</dt><dd>{tenant.name} <Badge tone="muted">{tenant.slug}</Badge></dd>
          <dt>API base</dt><dd className="mono dim">{conn.baseUrl}</dd>
          <dt>Key</dt><dd className="mono dim">{tenant.api_key_prefix}</dd>
          <dt>Quota</dt>
          <dd className="mono">
            {tenant.usage.runs_this_period} / {tenant.limits.monthly_run_quota} runs · $
            {tenant.usage.spend_usd.toFixed(4)} / ${tenant.limits.monthly_budget_usd}
          </dd>
        </dl>
        <p className="dim" style={{ fontSize: 11.5, lineHeight: 1.6 }}>
          Quotas are set by an administrator and can't be raised from here.
        </p>
        <button className="btn danger ghost sm" onClick={onDisconnect} style={{ marginTop: 6 }}>
          Remove this connection
        </button>
      </Card>

      <Card title="Isolation" sub="What this API key can reach">
        <dl className="kv" style={{ fontSize: 12.5 }}>
          <dt>Tenant</dt>
          <dd>{tenant.name}</dd>
          <dt>Tenant id</dt>
          <dd className="mono dim">{tenant.id}</dd>
          <dt>Key</dt>
          <dd className="mono dim">{tenant.api_key_prefix}</dd>
          <dt>Autonomy</dt>
          <dd>
            <Badge tone={tenant.policy.autonomy === "autonomous" ? "ok" : "warn"}>
              {tenant.policy.autonomy}
            </Badge>
          </dd>
        </dl>
        <p className="dim" style={{ fontSize: 11.5, marginTop: 12, marginBottom: 0, lineHeight: 1.6 }}>
          Every query this key makes is filtered by tenant id in the data layer, not by the caller.
          Another tenant's brands, runs, and assets are unreachable with it.
        </p>
      </Card>

      <DeveloperLogs conn={conn} />
    </div>
  );
}
