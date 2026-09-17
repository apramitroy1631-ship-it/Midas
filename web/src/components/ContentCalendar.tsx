import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import { Card, StatusBadge } from "./ui";
import { AssetEditor } from "./AssetEditor";
import { ChannelIcon } from "./ChannelIcon";
import type { Asset, Connection } from "../lib/types";

const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function dateKey(d: Date): string {
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

function statusDotTone(status: string): string {
  if (status === "published") return "var(--ok)";
  if (status === "published_partial") return "var(--warn)";
  if (status === "failed" || status === "abandoned") return "var(--danger)";
  return "var(--info)";
}

/**
 * A month grid built from the content library (assets), not raw runs — each
 * cell answers "what's here to look at or edit," which is asset-shaped, not
 * run-shaped. Every real day is clickable, not just days with something on
 * them: an empty day still needs to offer "go make something."
 */
export function ContentCalendar({
  conn,
  assets,
  onGoLaunch,
  onSaved,
}: {
  conn: Connection;
  assets: Asset[];
  onGoLaunch: () => void;
  onSaved?: () => void;
}) {
  const today = new Date();
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const [cursor, setCursor] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const [popover, setPopover] = useState<{ key: string; day: Date; top: number; left: number } | null>(null);
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setPopover(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const byDay = useMemo(() => {
    const map = new Map<string, Asset[]>();
    for (const a of assets) {
      const d = new Date(a.created_at);
      if (isNaN(d.getTime())) continue;
      const key = dateKey(d);
      (map.get(key) ?? map.set(key, []).get(key)!).push(a);
    }
    return map;
  }, [assets]);

  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const firstWeekday = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells: (Date | null)[] = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length: daysInMonth }, (_, i) => new Date(year, month, i + 1)),
  ];

  function openDay(e: MouseEvent<HTMLButtonElement>, d: Date) {
    const btn = e.currentTarget;
    const top = btn.offsetTop + btn.offsetHeight + 6;
    const left = Math.min(btn.offsetLeft, (bodyRef.current?.clientWidth ?? 400) - 260);
    const key = dateKey(d);
    setPopover((p) => (p?.key === key ? null : { key, day: d, top, left: Math.max(0, left) }));
  }

  const popoverAssets = popover ? byDay.get(popover.key) ?? [] : [];

  return (
    <Card
      title="Content calendar"
      sub="What's published, and what to make next"
      action={
        <div className="row gap-sm">
          <button className="btn ghost sm" onClick={() => { setCursor(new Date(year, month - 1, 1)); setPopover(null); }}>‹</button>
          <span className="cal-month-label">{MONTHS[month]} {year}</span>
          <button className="btn ghost sm" onClick={() => { setCursor(new Date(year, month + 1, 1)); setPopover(null); }}>›</button>
        </div>
      }
    >
      <div className="cal-body" ref={bodyRef}>
        <div className="cal-grid cal-head">
          {WEEKDAYS.map((w, i) => <div key={i} className="cal-weekday">{w}</div>)}
        </div>
        <div className="cal-grid">
          {cells.map((d, i) => {
            if (!d) return <div key={i} className="cal-cell empty" />;
            const key = dateKey(d);
            const dayAssets = byDay.get(key);
            const isToday = dateKey(d) === dateKey(today);
            const isSelected = popover?.key === key;
            return (
              <button
                key={i}
                className={
                  "cal-cell" +
                  (isToday ? " today" : "") +
                  (dayAssets ? " active" : "") +
                  (isSelected ? " selected" : "")
                }
                onClick={(e) => openDay(e, d)}
              >
                <span className="cal-cell-num">{d.getDate()}</span>
                {dayAssets && (
                  <span className="cal-dots">
                    {dayAssets.slice(0, 3).map((a, j) => (
                      <span key={j} className="cal-dot" style={{ background: statusDotTone(a.status) }} />
                    ))}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {popover && (
          <>
            <div className="cal-backdrop" onClick={() => setPopover(null)} />
            <div className="cal-popover" style={{ top: popover.top, left: popover.left }}>
              <div className="cal-popover-title">
                {popover.day.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" })}
              </div>
              {popoverAssets.length === 0 ? (
                <div className="col gap-sm" style={{ marginTop: 8 }}>
                  <div className="dim" style={{ fontSize: 12 }}>
                    {popover.day < todayStart
                      ? "Nothing was published on this day."
                      : "Nothing here yet."}
                  </div>
                  {popover.day >= todayStart && (
                    <button
                      className="btn primary sm"
                      onClick={() => { setPopover(null); onGoLaunch(); }}
                    >
                      Publish content for this campaign
                    </button>
                  )}
                </div>
              ) : (
                <div className="col gap-sm" style={{ marginTop: 8 }}>
                  {popoverAssets.map((a) => (
                    <button
                      key={a.id}
                      className="cal-day-run"
                      onClick={() => { setPopover(null); setEditingAsset(a); }}
                    >
                      <span className="cal-channel-icon"><ChannelIcon channel={a.channel} size={13} /></span>
                      <StatusBadge status={a.status} />
                      <span className="truncate" style={{ maxWidth: 190 }}>{a.headline || "Untitled"}</span>
                    </button>
                  ))}
                  {popover.day >= todayStart && (
                    <button
                      className="btn ghost sm"
                      onClick={() => { setPopover(null); onGoLaunch(); }}
                    >
                      + Publish new content
                    </button>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {editingAsset && (
        <AssetEditor
          asset={editingAsset}
          conn={conn}
          onClose={() => setEditingAsset(null)}
          onSaved={onSaved}
        />
      )}
    </Card>
  );
}
