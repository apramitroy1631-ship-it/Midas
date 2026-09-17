import { useMemo, useState } from "react";
import { ContentCalendar } from "../components/ContentCalendar";
import {
  Badge,
  Card,
  Empty,
  SectionHead,
  Stat,
  StatusBadge,
  duration,
  timeAgo,
} from "../components/ui";
import { api } from "../lib/api";
import type { Asset, AutopilotConfig, Connection, RunSummary, Stats, Tenant } from "../lib/types";

const QUIPS = [
  "Your campaigns are turning to gold.",
  "Autonomous marketing, zero micromanagement.",
  "Every run gets smarter than the last one.",
  "No human in the loop — just results.",
  "The agents never sleep. Neither does your growth.",
  "Built to think, built to ship.",
  "Precision, at machine speed.",
  "Consider your pipeline handled.",
];

function greetingWord(): string {
  const h = new Date().getHours();
  if (h < 5) return "Burning the midnight oil";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  if (h < 21) return "Good evening";
  return "Working late";
}

function displayName(conn: Connection, tenant: Tenant): string {
  if (conn.userEmail) {
    const local = conn.userEmail.split("@")[0];
    return local.charAt(0).toUpperCase() + local.slice(1);
  }
  return tenant.name;
}

function Greeting({ conn, tenant }: { conn: Connection; tenant: Tenant }) {
  const [quipIdx, setQuipIdx] = useState(() => Math.floor(Math.random() * QUIPS.length));
  const name = useMemo(() => displayName(conn, tenant), [conn, tenant]);

  function nextQuip() {
    setQuipIdx((i) => {
      let next = Math.floor(Math.random() * QUIPS.length);
      while (next === i && QUIPS.length > 1) next = Math.floor(Math.random() * QUIPS.length);
      return next;
    });
  }

  return (
    <div className="greeting">
      <div className="greeting-title">{greetingWord()}, {name}</div>
      <button className="greeting-quip" onClick={nextQuip} title="Click for another one">
        {QUIPS[quipIdx]} <span className="greeting-quip-hint">↻</span>
      </button>
    </div>
  );
}

export function Overview({
  conn,
  tenant,
  stats,
  runs,
  assets,
  autopilot,
  onRefresh,
  onOpenRun,
  onGoLaunch,
}: {
  conn: Connection;
  tenant: Tenant;
  stats: Stats | null;
  runs: RunSummary[];
  assets: Asset[];
  autopilot: AutopilotConfig | null;
  onRefresh: () => void;
  onOpenRun: (id: string) => void;
  onGoLaunch: () => void;
}) {
  const [ticking, setTicking] = useState(false);
  const [tickResult, setTickResult] = useState<string | null>(null);

  async function tick() {
    setTicking(true);
    setTickResult(null);
    try {
      const res = await api.autopilotTick(conn);
      setTickResult(
        res.skipped
          ? "Skipped: " + (res.reason ?? "not eligible")
          : `Completed run ${res.run_id?.slice(0, 8)} — ${res.status}`
      );
      onRefresh();
    } catch (err) {
      setTickResult(err instanceof Error ? err.message : String(err));
    } finally {
      setTicking(false);
    }
  }

  const quotaPct = tenant.limits.monthly_run_quota
    ? Math.round((tenant.usage.runs_this_period / tenant.limits.monthly_run_quota) * 100)
    : 0;

  return (
    <div className="col" style={{ gap: 0 }}>
      <Greeting conn={conn} tenant={tenant} />

      <ContentCalendar conn={conn} assets={assets} onGoLaunch={onGoLaunch} onSaved={onRefresh} />

      <div className="grid grid-4" style={{ marginTop: 14 }}>
        <Stat
          icon="◆"
          label="Campaign runs"
          value={stats?.total_runs ?? "—"}
          hint={`${stats?.published_runs ?? 0} published · ${stats?.failed_runs ?? 0} failed`}
        />
        <Stat
          icon="▤"
          label="Assets published"
          value={stats?.total_assets ?? "—"}
          hint="Live in the content library"
          tone="accent"
        />
        <Stat
          icon="◎"
          label="Self-directed runs"
          value={stats?.self_directed_runs ?? "—"}
          hint="Goal chosen by the system, not a person"
        />
        <Stat
          icon="↻"
          label="Avg revisions"
          value={stats?.avg_revisions ?? "—"}
          hint="Self-corrections before QA passed"
          tone={
            (stats?.avg_revisions ?? 0) > 1.5 ? "warn" : (stats?.avg_revisions ?? 0) > 0 ? "ok" : undefined
          }
        />
        <Card title="Quality" sub="Averaged across published runs" className="stat-quality-card">
          {stats?.avg_brand_safety || stats?.avg_goal_alignment ? (
            <div className="row" style={{ gap: 20 }}>
              <div>
                <div className="field-label">Brand safety</div>
                <div className="mono" style={{ fontSize: 22, fontWeight: 620 }}>
                  {stats?.avg_brand_safety ?? "—"}
                </div>
              </div>
              <div>
                <div className="field-label">Goal alignment</div>
                <div className="mono" style={{ fontSize: 22, fontWeight: 620 }}>
                  {stats?.avg_goal_alignment ?? "—"}
                </div>
              </div>
            </div>
          ) : (
            <div className="dim" style={{ fontSize: 12.5 }}>
              No published runs yet — scores appear once QA has reviewed something.
            </div>
          )}
        </Card>
      </div>

      {/* Autopilot card — pulled off the dashboard for now, kept here so it's a
          one-step re-add. Still fully wired: Settings can enable/disable the
          scheduler itself, this was only the manual "run one cycle now" view. */}
      {/*
      <div className="grid grid-2" style={{ marginTop: 14 }}>
        <Card
          title="Autopilot"
          sub="Unattended operation"
          action={
            <button className="btn sm" onClick={tick} disabled={ticking}>
              {ticking ? "Running…" : "Run cycle now"}
            </button>
          }
        >
          <div className="col gap-sm">
            <div className="row">
              <Badge tone={autopilot?.enabled ? "ok" : "muted"} dot={autopilot?.enabled}>
                {autopilot?.enabled ? "scheduled" : "off"}
              </Badge>
              {autopilot?.enabled && (
                <span className="mono dim" style={{ fontSize: 11.5 }}>
                  every {autopilot.interval_minutes}m
                </span>
              )}
            </div>
            <p className="muted" style={{ margin: "4px 0 0", fontSize: 12.5, lineHeight: 1.6 }}>
              {autopilot?.enabled
                ? `Next cycle ${autopilot.next_run_at ? timeAgo(autopilot.next_run_at).replace(" ago", " from the last run") : "when due"}. The Director picks its own goal from brand memory.`
                : "Turn this on in Settings and the system runs campaigns on a schedule with nobody present."}
            </p>
            {autopilot?.quota_block && (
              <div className="banner warn" style={{ marginTop: 10, marginBottom: 0 }}>
                <span>⚠</span>
                <div>{autopilot.quota_block}</div>
              </div>
            )}
            {tickResult && (
              <div className="mono dim" style={{ fontSize: 11.5, marginTop: 8 }}>
                {tickResult}
              </div>
            )}
          </div>
        </Card>
      </div>
      */}

      <div style={{ marginTop: 14 }}>
        <Card title="Usage this period" sub={tenant.usage.period}>
          <div className="col gap-sm">
            <div className="row" style={{ fontSize: 12.5 }}>
              <span className="muted">Runs</span>
              <span className="spacer" />
              <span className="mono">
                {tenant.usage.runs_this_period} / {tenant.limits.monthly_run_quota}
              </span>
            </div>
            <div className="meter">
              <div
                className="meter-fill"
                style={{
                  width: Math.min(100, quotaPct) + "%",
                  background: quotaPct > 85 ? "var(--danger)" : "var(--accent)",
                }}
              />
            </div>
            <div className="row" style={{ fontSize: 12.5, marginTop: 8 }}>
              <span className="muted">LLM spend</span>
              <span className="spacer" />
              <span className="mono">
                ${tenant.usage.spend_usd.toFixed(4)} / ${tenant.limits.monthly_budget_usd}
              </span>
            </div>
          </div>
        </Card>
      </div>

      <SectionHead
        action={
          <button className="btn sm ghost" onClick={onGoLaunch}>
            New run
          </button>
        }
      >
        Recent runs
      </SectionHead>

      <Card>
        {runs.length === 0 ? (
          <Empty
            icon="◆"
            title="Nothing has run yet"
            text="Launch a campaign and every agent step is recorded here."
            action={
              <button className="btn primary sm" onClick={onGoLaunch} style={{ marginTop: 8 }}>
                Launch a run
              </button>
            }
          />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Goal</th>
                  <th>Origin</th>
                  <th>Status</th>
                  <th>Rev</th>
                  <th>Assets</th>
                  <th>Align</th>
                  <th>Time</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {runs.slice(0, 8).map((r) => (
                  <tr key={r.id} onClick={() => onOpenRun(r.id)}>
                    <td className="truncate" style={{ maxWidth: 320 }}>{r.goal || "—"}</td>
                    <td>
                      <Badge tone={r.goal_origin === "self-directed" ? "info" : "muted"}>
                        {r.goal_origin === "self-directed" ? "self" : "operator"}
                      </Badge>
                    </td>
                    <td><StatusBadge status={r.status} /></td>
                    <td className="mono">{r.revisions}</td>
                    <td className="mono">{r.asset_count}</td>
                    <td className="mono">{r.goal_alignment_score ?? "—"}</td>
                    <td className="mono dim">{duration(r.duration_ms)}</td>
                    <td className="dim">{timeAgo(r.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
