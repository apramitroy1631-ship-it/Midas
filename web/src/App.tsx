import { useCallback, useEffect, useState } from "react";
import { Badge, initials } from "./components/ui";
import { api } from "./lib/api";
import { store } from "./lib/store";
import type {
  Asset,
  AuditEntry,
  AutopilotConfig,
  Brand,
  Connection,
  RunSummary,
  Stats,
  Tenant,
} from "./lib/types";
import { Audit } from "./views/Audit";
import { Brands } from "./views/Brands";
import { Connect } from "./views/Connect";
import { Launch } from "./views/Launch";
import { Library } from "./views/Library";
import { Overview } from "./views/Overview";
import { Runs } from "./views/Runs";
import { Settings } from "./views/Settings";

type View = "overview" | "launch" | "runs" | "library" | "brands" | "audit" | "settings";

const NAV: { id: View; label: string; icon: string; group: string }[] = [
  { id: "overview", label: "Mission control", icon: "◎", group: "Operate" },
  { id: "launch", label: "Launch run", icon: "▶", group: "Operate" },
  { id: "runs", label: "Runs", icon: "◆", group: "Operate" },
  { id: "library", label: "Content library", icon: "▤", group: "Output" },
  { id: "audit", label: "Decision log", icon: "≡", group: "Output" },
  { id: "brands", label: "Brands", icon: "◇", group: "Configure" },
  { id: "settings", label: "Settings", icon: "⚙", group: "Configure" },
];

const TITLES: Record<View, string> = {
  overview: "Mission control",
  launch: "Launch an autonomous run",
  runs: "Runs",
  library: "Content library",
  brands: "Brands",
  audit: "Decision log",
  settings: "Settings",
};

export default function App() {
  const [conn, setConn] = useState<Connection | null>(() => store.active());
  const [connections, setConnections] = useState<Connection[]>(() => store.connections());
  const [adding, setAdding] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">(() => store.theme());

  const [view, setView] = useState<View>("overview");
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const [openRunId, setOpenRunId] = useState<string | null>(null);

  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [autopilot, setAutopilot] = useState<AutopilotConfig | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    store.setTheme(theme);
  }, [theme]);

  const refresh = useCallback(async () => {
    if (!conn) return;
    setLoadError(null);
    try {
      const [t, b, r, a, au, s, ap] = await Promise.all([
        api.me(conn),
        api.brands(conn),
        api.runs(conn),
        api.assets(conn),
        api.audit(conn),
        api.stats(conn),
        api.autopilot(conn),
      ]);
      setTenant(t);
      setBrands(b);
      setRuns(r);
      setAssets(a);
      setAudit(au);
      setStats(s);
      setAutopilot(ap);
    } catch (err) {
      setLoadError(
        err instanceof Error
          ? err.message === "Failed to fetch"
            ? "Can't reach the API at " + conn.baseUrl
            : err.message
          : String(err)
      );
    }
  }, [conn]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Close the tenant switcher on any outside click.
  useEffect(() => {
    if (!switcherOpen) return;
    const close = () => setSwitcherOpen(false);
    window.addEventListener("click", close);
    return () => window.removeEventListener("click", close);
  }, [switcherOpen]);

  function selectConnection(c: Connection) {
    store.setActive(c.id);
    setConn(c);
    setTenant(null);
    setBrands([]);
    setRuns([]);
    setAssets([]);
    setAudit([]);
    setStats(null);
    setOpenRunId(null);
    setView("overview");
  }

  function disconnect() {
    if (!conn) return;
    store.remove(conn.id);
    const remaining = store.connections();
    setConnections(remaining);
    setConn(remaining[0] ?? null);
    setTenant(null);
  }

  if (!conn || adding) {
    return (
      <Connect
        onConnected={(c) => {
          setConnections(store.connections());
          setAdding(false);
          selectConnection(c);
        }}
        onCancel={adding && conn ? () => setAdding(false) : undefined}
      />
    );
  }

  const grouped = NAV.reduce<Record<string, typeof NAV>>((acc, item) => {
    (acc[item.group] ??= []).push(item);
    return acc;
  }, {});

  const counts: Partial<Record<View, number>> = {
    runs: runs.length,
    library: assets.length,
    brands: brands.length,
    audit: audit.length,
  };

  return (
    <div className="app">
      <nav className="sidebar">
        <div className="logo">
          <div className="logo-mark">BX</div>
          <div>
            <div className="logo-text">BuildX</div>
            <div className="logo-sub">AUTONOMOUS</div>
          </div>
        </div>

        {Object.entries(grouped).map(([group, items]) => (
          <div key={group}>
            <div className="nav-label">{group}</div>
            {items.map((item) => (
              <button
                key={item.id}
                className={"nav-item" + (view === item.id ? " active" : "")}
                onClick={() => {
                  setView(item.id);
                  setOpenRunId(null);
                }}
              >
                <span className="nav-icon">{item.icon}</span>
                {item.label}
                {counts[item.id] !== undefined && counts[item.id]! > 0 && (
                  <span className="nav-count">{counts[item.id]}</span>
                )}
              </button>
            ))}
          </div>
        ))}

        <div className="spacer" />

        <button className="nav-item" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
          <span className="nav-icon">{theme === "dark" ? "☾" : "☀"}</span>
          {theme === "dark" ? "Dark" : "Light"}
        </button>
      </nav>

      <div className="main">
        <header className="topbar">
          <h1>{TITLES[view]}</h1>
          {tenant?.policy.autonomy === "autonomous" && (
            <Badge tone="ok" dot>no human in the loop</Badge>
          )}
          <div className="topbar-spacer" />

          <button className="btn ghost sm" onClick={() => void refresh()}>Refresh</button>

          <div
            className="tenant-switch"
            onClick={(e) => {
              e.stopPropagation();
              setSwitcherOpen((v) => !v);
            }}
          >
            <span className="tenant-avatar" style={{ background: conn.color }}>
              {initials(tenant?.name ?? conn.label)}
            </span>
            <div style={{ lineHeight: 1.25 }}>
              <div className="tenant-name">{tenant?.name ?? conn.label}</div>
              <div className="tenant-meta">{tenant?.slug ?? "connecting…"}</div>
            </div>
            <span className="dim" style={{ fontSize: 10 }}>▾</span>
          </div>

          {switcherOpen && (
            <div className="dropdown" onClick={(e) => e.stopPropagation()}>
              {connections.map((c) => (
                <button
                  key={c.id}
                  className="dropdown-item"
                  onClick={() => {
                    selectConnection(c);
                    setSwitcherOpen(false);
                  }}
                >
                  <span className="tenant-avatar" style={{ background: c.color }}>
                    {initials(c.label)}
                  </span>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div className="tenant-name">{c.label}</div>
                    <div className="tenant-meta truncate">{c.baseUrl}</div>
                  </div>
                  {c.id === conn.id && <span style={{ color: "var(--accent)" }}>✓</span>}
                </button>
              ))}
              <div className="dropdown-sep" />
              <button
                className="dropdown-item"
                onClick={() => {
                  setAdding(true);
                  setSwitcherOpen(false);
                }}
              >
                <span className="nav-icon">＋</span>
                Connect another tenant
              </button>
            </div>
          )}
        </header>

        <main className="content">
          {loadError && (
            <div className="banner danger">
              <span>✕</span>
              <div>
                <strong>Connection problem.</strong> {loadError}
              </div>
            </div>
          )}

          {!tenant && !loadError && <div className="dim">Loading tenant…</div>}

          {tenant && view === "overview" && (
            <Overview
              conn={conn}
              tenant={tenant}
              stats={stats}
              runs={runs}
              autopilot={autopilot}
              onRefresh={refresh}
              onOpenRun={(id) => {
                setOpenRunId(id);
                setView("runs");
              }}
              onGoLaunch={() => setView("launch")}
            />
          )}

          {tenant && view === "launch" && (
            <Launch conn={conn} tenant={tenant} brands={brands} onFinished={refresh} />
          )}

          {tenant && view === "runs" && (
            <Runs
              conn={conn}
              runs={runs}
              openRunId={openRunId}
              onOpenRun={setOpenRunId}
              onCloseRun={() => setOpenRunId(null)}
            />
          )}

          {tenant && view === "library" && <Library assets={assets} brands={brands} />}

          {tenant && view === "brands" && (
            <Brands conn={conn} brands={brands} onChanged={refresh} />
          )}

          {tenant && view === "audit" && <Audit entries={audit} />}

          {tenant && view === "settings" && (
            <Settings
              conn={conn}
              tenant={tenant}
              brands={brands}
              autopilot={autopilot}
              onSaved={refresh}
              onDisconnect={disconnect}
            />
          )}
        </main>
      </div>
    </div>
  );
}
