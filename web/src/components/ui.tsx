import { useEffect, type ReactNode } from "react";

/* --- primitives ---------------------------------------------------------- */

export function Card({
  title,
  sub,
  action,
  children,
  className = "",
}: {
  title?: string;
  sub?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={"card " + className}>
      {(title || action) && (
        <div className="card-head">
          <div style={{ minWidth: 0 }}>
            {title && <h3 className="card-title">{title}</h3>}
            {sub && <p className="card-sub">{sub}</p>}
          </div>
          <div className="spacer" />
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

export function Stat({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "ok" | "warn" | "danger" | "accent";
}) {
  const color =
    tone === "ok" ? "var(--ok)"
    : tone === "warn" ? "var(--warn)"
    : tone === "danger" ? "var(--danger)"
    : tone === "accent" ? "var(--accent)"
    : "var(--text)";
  return (
    <div className="card stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value" style={{ color }}>{value}</span>
      {hint && <span className="stat-hint">{hint}</span>}
    </div>
  );
}

export function Badge({
  tone = "muted",
  children,
  dot,
}: {
  tone?: "ok" | "warn" | "danger" | "info" | "muted";
  children: ReactNode;
  dot?: boolean;
}) {
  return (
    <span className={"badge " + tone}>
      {dot && <span className="dot" style={{ background: "currentColor" }} />}
      {children}
    </span>
  );
}

/** Maps a run status to the badge that reads correctly at a glance. */
export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, ["ok" | "warn" | "danger" | "info" | "muted", string]> = {
    published: ["ok", "published"],
    published_partial: ["warn", "partial publish"],
    review_pending: ["info", "awaiting review"],
    abandoned: ["danger", "abandoned"],
    failed: ["danger", "failed"],
    running: ["info", "running"],
  };
  const [tone, label] = map[status] ?? ["muted", status];
  return <Badge tone={tone}>{label}</Badge>;
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export function Toggle({ on, onChange }: { on: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      className={"toggle" + (on ? " on" : "")}
      onClick={() => onChange(!on)}
      aria-pressed={on}
    />
  );
}

export function ToggleRow({
  title,
  desc,
  on,
  onChange,
}: {
  title: string;
  desc: string;
  on: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="toggle-row">
      <div className="toggle-row-text">
        <div className="toggle-row-title">{title}</div>
        <div className="toggle-row-desc">{desc}</div>
      </div>
      <Toggle on={on} onChange={onChange} />
    </div>
  );
}

export function Empty({
  icon = "◌",
  title,
  text,
  action,
}: {
  icon?: string;
  title: string;
  text?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">{icon}</div>
      <div className="empty-title">{title}</div>
      {text && <div className="empty-text">{text}</div>}
      {action}
    </div>
  );
}

export function Json({ data }: { data: unknown }) {
  return <pre className="json">{JSON.stringify(data, null, 2)}</pre>;
}

export function Chips({ items }: { items: (string | undefined)[] }) {
  const clean = items.filter(Boolean) as string[];
  if (!clean.length) return null;
  return (
    <div className="chips">
      {clean.map((c, i) => (
        <span className="chip" key={i}>{c}</span>
      ))}
    </div>
  );
}

export function Meter({ value, max = 100, tone }: { value: number; max?: number; tone?: string }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const color = tone ?? (pct >= 80 ? "var(--ok)" : pct >= 55 ? "var(--warn)" : "var(--danger)");
  return (
    <div className="meter">
      <div className="meter-fill" style={{ width: pct + "%", background: color }} />
    </div>
  );
}

export function Drawer({
  title,
  subtitle,
  onClose,
  children,
}: {
  title: string;
  subtitle?: ReactNode;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer">
        <div className="drawer-head">
          <div style={{ minWidth: 0 }}>
            <h3 className="card-title">{title}</h3>
            {subtitle && <p className="card-sub">{subtitle}</p>}
          </div>
          <div className="spacer" />
          <button className="btn ghost sm" onClick={onClose}>Close</button>
        </div>
        <div className="drawer-body">{children}</div>
      </aside>
    </>
  );
}

export function SectionHead({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="section-head">
      <h2>{children}</h2>
      <span className="rule" />
      {action}
    </div>
  );
}

/* --- formatting helpers -------------------------------------------------- */

export function timeAgo(iso: string): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  const secs = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (secs < 60) return secs + "s ago";
  if (secs < 3600) return Math.floor(secs / 60) + "m ago";
  if (secs < 86400) return Math.floor(secs / 3600) + "h ago";
  return Math.floor(secs / 86400) + "d ago";
}

export function duration(ms: number): string {
  if (!ms) return "—";
  return ms < 1000 ? ms + "ms" : (ms / 1000).toFixed(1) + "s";
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}
