import { useMemo, useState } from "react";
import { Card, StatusBadge, timeAgo } from "./ui";
import type { RunSummary } from "../lib/types";

const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function dateKey(d: Date): string {
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

/**
 * A month grid built from existing run history — no new backend endpoint,
 * just `created_at` grouped by calendar day. Clicking a day with activity
 * expands its runs inline instead of navigating away, so glancing at the
 * month stays a one-click, not a page change.
 */
export function ContentCalendar({
  runs,
  onOpenRun,
}: {
  runs: RunSummary[];
  onOpenRun: (id: string) => void;
}) {
  const today = new Date();
  const [cursor, setCursor] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const [selected, setSelected] = useState<string | null>(null);

  const byDay = useMemo(() => {
    const map = new Map<string, RunSummary[]>();
    for (const r of runs) {
      const d = new Date(r.created_at);
      if (isNaN(d.getTime())) continue;
      const key = dateKey(d);
      (map.get(key) ?? map.set(key, []).get(key)!).push(r);
    }
    return map;
  }, [runs]);

  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const firstWeekday = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells: (Date | null)[] = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length: daysInMonth }, (_, i) => new Date(year, month, i + 1)),
  ];

  const selectedRuns = selected ? byDay.get(selected) ?? [] : [];

  function statusDotTone(status: string): string {
    if (status === "published") return "var(--ok)";
    if (status === "published_partial") return "var(--warn)";
    if (status === "failed" || status === "abandoned") return "var(--danger)";
    return "var(--info)";
  }

  return (
    <Card
      title="Content calendar"
      sub="What ran, day by day"
      action={
        <div className="row gap-sm">
          <button className="btn ghost sm" onClick={() => { setCursor(new Date(year, month - 1, 1)); setSelected(null); }}>‹</button>
          <span className="mono dim" style={{ fontSize: 12, minWidth: 108, textAlign: "center" }}>
            {MONTHS[month]} {year}
          </span>
          <button className="btn ghost sm" onClick={() => { setCursor(new Date(year, month + 1, 1)); setSelected(null); }}>›</button>
        </div>
      }
    >
      <div className="cal-grid cal-head">
        {WEEKDAYS.map((w, i) => <div key={i} className="cal-weekday">{w}</div>)}
      </div>
      <div className="cal-grid">
        {cells.map((d, i) => {
          if (!d) return <div key={i} className="cal-cell empty" />;
          const key = dateKey(d);
          const dayRuns = byDay.get(key);
          const isToday = dateKey(d) === dateKey(today);
          const isSelected = selected === key;
          return (
            <button
              key={i}
              className={
                "cal-cell" +
                (isToday ? " today" : "") +
                (dayRuns ? " active" : "") +
                (isSelected ? " selected" : "")
              }
              onClick={() => dayRuns && setSelected(isSelected ? null : key)}
              disabled={!dayRuns}
            >
              <span className="cal-cell-num">{d.getDate()}</span>
              {dayRuns && (
                <span className="cal-dots">
                  {dayRuns.slice(0, 3).map((r, j) => (
                    <span key={j} className="cal-dot" style={{ background: statusDotTone(r.status) }} />
                  ))}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {selected && (
        <div className="cal-day-detail">
          {selectedRuns.length === 0 ? (
            <div className="dim" style={{ fontSize: 12 }}>Nothing on this day.</div>
          ) : (
            <div className="col gap-sm">
              {selectedRuns.map((r) => (
                <button key={r.id} className="cal-day-run" onClick={() => onOpenRun(r.id)}>
                  <StatusBadge status={r.status} />
                  <span className="truncate" style={{ maxWidth: 260 }}>{r.goal || "Untitled run"}</span>
                  <span className="spacer" />
                  <span className="dim mono" style={{ fontSize: 11 }}>{timeAgo(r.created_at)}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
