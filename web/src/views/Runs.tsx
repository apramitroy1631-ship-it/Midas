import { useEffect, useMemo, useState } from "react";
import { AgentRail } from "../components/AgentRail";
import {
  Badge,
  Card,
  Drawer,
  Empty,
  Field,
  StatusBadge,
  duration,
  timeAgo,
} from "../components/ui";
import { api } from "../lib/api";
import type { Brand, Connection, RunDetail, RunSummary } from "../lib/types";

export function Runs({
  conn,
  runs,
  brands,
  openRunId,
  onCloseRun,
  onOpenRun,
}: {
  conn: Connection;
  runs: RunSummary[];
  brands: Brand[];
  openRunId: string | null;
  onCloseRun: () => void;
  onOpenRun: (id: string) => void;
}) {
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [brandId, setBrandId] = useState("");
  const [search, setSearch] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const fromTime = from ? new Date(from).getTime() : null;
    const toTime = to ? new Date(to).getTime() + 86_400_000 - 1 : null;
    return runs.filter((r) => {
      if (brandId && r.brand_id !== brandId) return false;
      if (q && !r.goal.toLowerCase().includes(q)) return false;
      const created = new Date(r.created_at).getTime();
      if (fromTime && created < fromTime) return false;
      if (toTime && created > toTime) return false;
      return true;
    });
  }, [runs, brandId, search, from, to]);
  const anyFilterActive = !!(brandId || search || from || to);

  useEffect(() => {
    if (!openRunId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    api
      .run(conn, openRunId)
      .then((d) => !cancelled && setDetail(d))
      .catch(() => !cancelled && setDetail(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [conn, openRunId]);

  return (
    <>
      <Card title="Run history" sub={`${runs.length} runs`}>
        {runs.length === 0 ? (
          <Empty icon="◆" title="No runs yet" text="Every campaign the system executes is recorded here with its full agent trace." />
        ) : (
          <>
            <div className="row wrap" style={{ marginBottom: 12 }}>
              <input
                className="input"
                style={{ maxWidth: 320 }}
                placeholder="Search goal…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <select className="select" style={{ width: 180 }} value={brandId} onChange={(e) => setBrandId(e.target.value)}>
                <option value="">All brands</option>
                {brands.map((b) => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
              <Field label="From"><input className="input mono" type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></Field>
              <Field label="To"><input className="input mono" type="date" value={to} onChange={(e) => setTo(e.target.value)} /></Field>
              <span className="spacer" />
              <div className="row" style={{ alignSelf: "flex-end", marginBottom: 13 }}>
                {anyFilterActive && (
                  <button className="btn ghost sm" onClick={() => { setBrandId(""); setSearch(""); setFrom(""); setTo(""); }}>
                    Clear filters
                  </button>
                )}
                <span className="mono dim">{filtered.length} / {runs.length}</span>
              </div>
            </div>
          {filtered.length === 0 ? (
            <Empty icon="◆" title="Nothing matches" text="Try clearing a filter or broadening the search." />
          ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Goal</th>
                  <th>Brand</th>
                  <th>Trigger</th>
                  <th>Status</th>
                  <th>Rev</th>
                  <th>Assets</th>
                  <th>Safety</th>
                  <th>Align</th>
                  <th>Time</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.id} onClick={() => onOpenRun(r.id)}>
                    <td className="truncate" style={{ maxWidth: 280 }}>
                      {r.goal || "—"}
                      {r.goal_origin === "self-directed" && (
                        <span style={{ marginLeft: 7 }}><Badge tone="info">self</Badge></span>
                      )}
                    </td>
                    <td className="muted">{r.brand_name}</td>
                    <td><Badge tone={r.trigger === "autopilot" ? "info" : "muted"}>{r.trigger}</Badge></td>
                    <td><StatusBadge status={r.status} /></td>
                    <td className="mono">{r.revisions}</td>
                    <td className="mono">{r.asset_count}</td>
                    <td className="mono">{r.brand_safety_score ?? "—"}</td>
                    <td className="mono">{r.goal_alignment_score ?? "—"}</td>
                    <td className="mono dim">{duration(r.duration_ms)}</td>
                    <td className="dim">{timeAgo(r.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )}
          </>
        )}
      </Card>

      {openRunId && (
        <Drawer
          title={detail?.goal || "Run detail"}
          subtitle={
            detail ? (
              <span className="row gap-sm" style={{ display: "inline-flex" }}>
                <span className="mono">{detail.id.slice(0, 8)}</span>
                <StatusBadge status={detail.status} />
                <Badge tone={detail.goal_origin === "self-directed" ? "info" : "muted"}>
                  {detail.goal_origin}
                </Badge>
              </span>
            ) : undefined
          }
          onClose={onCloseRun}
        >
          {loading && <div className="dim">Loading…</div>}
          {!loading && !detail && <Empty icon="✕" title="Run not found" />}
          {detail && (
            <>
              <div className="grid grid-4" style={{ marginBottom: 18 }}>
                <div><div className="field-label">Revisions</div><div className="mono" style={{ fontSize: 18 }}>{detail.revisions}</div></div>
                <div><div className="field-label">Assets</div><div className="mono" style={{ fontSize: 18 }}>{detail.asset_count}</div></div>
                <div><div className="field-label">Duration</div><div className="mono" style={{ fontSize: 18 }}>{duration(detail.duration_ms)}</div></div>
                <div><div className="field-label">LLM cost</div><div className="mono" style={{ fontSize: 18 }}>${(detail.usage as any)?.cost_usd ?? 0}</div></div>
              </div>

              {detail.error && (
                <div className="banner danger">
                  <span>✕</span>
                  <div><strong>Failed.</strong> {detail.error}</div>
                </div>
              )}

              {!!detail.dropped_channels?.length && (
                <div className="banner warn">
                  <span>⚖</span>
                  <div>
                    <strong>Arbitrated.</strong> Dropped after the revision budget ran out:{" "}
                    {detail.dropped_channels.join(", ")}.
                  </div>
                </div>
              )}

              <div className="field-label" style={{ marginBottom: 10 }}>Agent trace</div>
              <AgentRail steps={detail.events ?? []} running={false} error={null} />
            </>
          )}
        </Drawer>
      )}
    </>
  );
}
