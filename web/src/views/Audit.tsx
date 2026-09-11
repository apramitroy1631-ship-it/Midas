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
            {entries.map((e) => (
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
      <p className="dim" style={{ fontSize: 11.5, marginTop: 14, marginBottom: 0, lineHeight: 1.6 }}>
        Every entry is written by the system itself. There is no human approver to attribute, which is
        exactly why the record of what it decided — and what it dropped — matters.
      </p>
    </Card>
  );
}
