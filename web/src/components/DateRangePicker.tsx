import { useEffect, useRef, useState } from "react";

const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function toKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function fromKey(key: string): Date | null {
  if (!key) return null;
  const [y, m, d] = key.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function short(d: Date): string {
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** A click-to-pick calendar range, in place of two bare native date inputs —
 * same visual language as the Dashboard's content calendar. First click sets
 * the start, second click (on or after it) sets the end and closes; clicking
 * before the start restarts the selection instead of erroring. */
export function DateRangePicker({
  from,
  to,
  onChange,
  minDate,
}: {
  from: string;
  to: string;
  onChange: (from: string, to: string) => void;
  /** "YYYY-MM-DD" — days before this are shown but not selectable. Used to keep
   * scheduling pickers from picking a date that's already passed. */
  minDate?: string;
}) {
  const [open, setOpen] = useState(false);
  const today = new Date();
  const [cursor, setCursor] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  const fromDate = fromKey(from);
  const toDate = fromKey(to);
  const minD = minDate ? fromKey(minDate) : null;

  function pick(d: Date) {
    if (minD && d < minD) return;
    if (!fromDate || (fromDate && toDate)) {
      onChange(toKey(d), "");
      return;
    }
    if (d < fromDate) {
      onChange(toKey(d), "");
      return;
    }
    onChange(from, toKey(d));
    setOpen(false);
  }

  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const firstWeekday = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (Date | null)[] = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length: daysInMonth }, (_, i) => new Date(year, month, i + 1)),
  ];

  const label =
    fromDate && toDate
      ? `${short(fromDate)} – ${short(toDate)}`
      : fromDate
      ? `${short(fromDate)} – …`
      : "Any date";

  return (
    <div className="drp" ref={rootRef}>
      <button type="button" className="drp-trigger" onClick={() => setOpen((o) => !o)}>
        <span aria-hidden>📅</span> {label}
      </button>
      {(from || to) && (
        <button
          type="button"
          className="drp-clear"
          title="Clear date filter"
          onClick={() => { onChange("", ""); setOpen(false); }}
        >
          ✕
        </button>
      )}

      {open && (
        <div className="drp-pop">
          <div className="row" style={{ marginBottom: 8 }}>
            <button type="button" className="btn ghost sm" onClick={() => setCursor(new Date(year, month - 1, 1))}>‹</button>
            <span className="cal-month-label" style={{ flex: 1, textAlign: "center" }}>{MONTHS[month]} {year}</span>
            <button type="button" className="btn ghost sm" onClick={() => setCursor(new Date(year, month + 1, 1))}>›</button>
          </div>
          <div className="cal-grid cal-head">
            {WEEKDAYS.map((w, i) => <div key={i} className="cal-weekday">{w}</div>)}
          </div>
          <div className="cal-grid drp-grid">
            {cells.map((d, i) => {
              if (!d) return <div key={i} className="cal-cell empty" />;
              const isFrom = fromDate && toKey(d) === toKey(fromDate);
              const isTo = toDate && toKey(d) === toKey(toDate);
              const inRange = fromDate && toDate && d > fromDate && d < toDate;
              const isToday = toKey(d) === toKey(today);
              const disabled = !!(minD && d < minD);
              return (
                <button
                  key={i}
                  type="button"
                  className={
                    "cal-cell drp-day" +
                    (isToday ? " today" : "") +
                    (isFrom || isTo ? " drp-endpoint" : "") +
                    (inRange ? " drp-inrange" : "") +
                    (disabled ? " disabled" : "")
                  }
                  disabled={disabled}
                  onClick={() => pick(d)}
                >
                  <span className="cal-cell-num">{d.getDate()}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
