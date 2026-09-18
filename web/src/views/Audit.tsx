import { useMemo, useState } from "react";
import { Badge, Card, Empty, timeAgo } from "../components/ui";
import type { AuditEntry } from "../lib/types";

const TONE: Record<string, "ok" | "warn" | "danger" | "info" | "muted"> = {
  "run.published": "ok",
  "run.published_partial": "warn",
  "run.review_pending": "info",
  "run.abandoned": "danger",
  "run.failed": "danger",
};

export function Audit({ entries }: { entries: AuditEntry[] }) {
  const [search, setSearch] = useState("");
  const [origins, setOrigins] = useState<string[]>([]);
  const [triggers, setTriggers] = useState<string[]>([]);
  const [actors, setActors] = useState<string[]>([]);

  const knownTriggers = useMemo(() => Array.from(new Set(entries.map((e) => e.trigger))).sort(), [entries]);
  const knownActors = useMemo(() => Array.from(new Set(entries.map((e) => e.actor))).sort(), [entries]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return entries.filter((e) => {
      const origin = e.detail?.goal_origin === "self-directed" ? "self-directed" : "operator";
      if (origins.length && !origins.includes(origin)) return false;
      if (triggers.length && !triggers.includes(e.trigger)) return false;
      if (actors.length && !actors.includes(e.actor)) return false;
      if (q && !String(e.detail?.goal || "").toLowerCase().includes(q)) return false;
      return true;
    });
  }, [entries, search, origins, triggers, actors]);

  const anyFilterActive = !!(search || origins.length || triggers.length || actors.length);

  function toggleIn(list: string[], setList: (v: string[]) => void, value: string) {
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
  }

  if (!entries.length) {
    return (
      <Empty
        icon="▤"
        title="No decisions logged yet"
        text="Because no person approves anything, every outcome the system reaches is recorded here instead — what it did, why, and what it cost."
      />
    );
  }

  return (
    <Card title="Decision log" sub={`${entries.length} entries · newest first`}>
      <div className="row wrap" style={{ marginBottom: 12 }}>
        <input
          className="input"
          style={{ maxWidth: 300 }}
          placeholder="Search goal…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <div className="row wrap" style={{ marginBottom: 12 }}>
        <span className="field-label" style={{ margin: 0, alignSelf: "center" }}>Origin</span>
        {["operator", "self-directed"].map((o) => (
          <button
            key={o}
            type="button"
            className={"chip-toggle" + (origins.includes(o) ? " active" : "")}
            onClick={() => toggleIn(origins, setOrigins, o)}
          >
            {o === "self-directed" ? "self" : "operator"}
          </button>
        ))}
        <span className="field-label" style={{ margin: "0 0 0 10px", alignSelf: "center" }}>Trigger</span>
        {knownTriggers.map((t) => (
          <button
            key={t}
            type="button"
            className={"chip-toggle" + (triggers.includes(t) ? " active" : "")}
            onClick={() => toggleIn(triggers, setTriggers, t)}
          >
            {t}
          </button>
        ))}
        <span className="field-label" style={{ margin: "0 0 0 10px", alignSelf: "center" }}>Actor</span>
        {knownActors.map((a) => (
          <button
            key={a}
            type="button"
            className={"chip-toggle" + (actors.includes(a) ? " active" : "")}
            onClick={() => toggleIn(actors, setActors, a)}
          >
            {a}
          </button>
        ))}
        <span className="spacer" />
        <div className="row" style={{ alignSelf: "center" }}>
          {anyFilterActive && (
            <button
              className="btn ghost sm"
              onClick={() => { setSearch(""); setOrigins([]); setTriggers([]); setActors([]); }}
            >
              Clear filters
            </button>
          )}
          <span className="mono dim">{filtered.length} / {entries.length}</span>
        </div>
      </div>

      {filtered.length === 0 ? (
        <Empty icon="▤" title="Nothing matches" text="Try clearing a filter or broadening the search." />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Action</th>
                <th>Goal</th>
                <th>Origin</th>
                <th>Trigger</th>
                <th>Rev</th>
                <th>Assets</th>
                <th>Cost</th>
                <th>Actor</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((e) => (
                <tr key={e.id} style={{ cursor: "default" }}>
                  <td><Badge tone={TONE[e.action] ?? "muted"}>{e.action.replace("run.", "")}</Badge></td>
                  <td className="truncate muted" style={{ maxWidth: 300 }}>{e.detail?.goal || "—"}</td>
                  <td>
                    <Badge tone={e.detail?.goal_origin === "self-directed" ? "info" : "muted"}>
                      {e.detail?.goal_origin === "self-directed" ? "self" : "operator"}
                    </Badge>
                  </td>
                  <td className="mono dim">{e.trigger}</td>
                  <td className="mono">{e.detail?.revisions ?? 0}</td>
                  <td className="mono">{e.detail?.assets ?? 0}</td>
                  <td className="mono dim">${e.detail?.cost_usd ?? 0}</td>
                  <td className="mono dim">{e.actor}</td>
                  <td className="dim">{timeAgo(e.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="dim" style={{ fontSize: 11.5, marginTop: 14, marginBottom: 0, lineHeight: 1.6 }}>
        Every entry is written by the system itself. There is no human approver to attribute, which is
        exactly why the record of what it decided — and what it dropped — matters.
      </p>
    </Card>
  );
}
