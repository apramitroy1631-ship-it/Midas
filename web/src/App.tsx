import { useCallback, useEffect, useState } from "react";
import { Badge } from "./components/ui";
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

// Labels are written for someone opening this for the first time, not for
// whoever built it — "Dashboard" over "Mission Control", "New Campaign"
// over "Launch run", etc. Each pairs with a one-line sub-label in the nav
// so the section header alone doesn't have to carry all the meaning.
const NAV: { id: View; label: string; sub: string; icon: string; group: string }[] = [
  { id: "overview", label: "Dashboard", sub: "How things are going", icon: "◎", group: "Operate" },
  { id: "launch", label: "New Campaign", sub: "Start an autonomous run", icon: "▶", group: "Operate" },
  { id: "runs", label: "Campaign History", sub: "Every run, replayable", icon: "◆", group: "Operate" },
  { id: "library", label: "Content Library", sub: "Everything published", icon: "▤", group: "Output" },
  { id: "audit", label: "Decision Log", sub: "Why each run did what it did", icon: "≡", group: "Output" },
  { id: "brands", label: "Brands", sub: "Voice, USP, hard rules", icon: "◇", group: "Configure" },
  { id: "settings", label: "Settings", sub: "Autonomy & guardrails", icon: "⚙", group: "Configure" },
];

const TITLES: Record<View, string> = {
  overview: "Dashboard",
  launch: "New Campaign",
  runs: "Campaign History",
  library: "Content Library",
  brands: "Brands",
  audit: "Decision Log",
  settings: "Settings",
};

export default function App() {
  const [conn, setConn] = useState<Connection | null>(() => store.active());
  const [theme, setTheme] = useState<"dark" | "light">(() => store.theme());

  const [view, setView] = useState<View>("overview");
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

  function disconnect() {
    if (!conn) return;
    store.remove(conn.id);
    setConn(store.connections()[0] ?? null);
    setTenant(null);
  }

  if (!conn) {
    return (
      <Connect
        onConnected={(c) => {
          store.setActive(c.id);
          setConn(c);
          setView("overview");
        }}
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
          <div className="logo-mark">M</div>
          <div>
            <div className="logo-text">MIDAS</div>
            <div className="logo-sub">MARKETING AUTOMATION</div>
          </div>
        </div>

        {Object.entries(grouped).map(([group, items]) => (
          <div key={group}>
            <div className="nav-label">{group}</div>
            {items.map((item) => (
              <button
                key={item.id}
                className={"nav-item" + (view === item.id ? " active" : "")}
                title={item.sub}
                onClick={() => {
                  setView(item.id);
                  setOpenRunId(null);
                }}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-item-text">
                  <span className="nav-item-label">{item.label}</span>
                  <span className="nav-item-sub">{item.sub}</span>
                </span>
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
          <span className="nav-item-text">
            <span className="nav-item-label">{theme === "dark" ? "Dark" : "Light"}</span>
          </span>
        </button>
      </nav>

      <div className="main">
        <header className="topbar">
          <div>
            <h1>{TITLES[view]}</h1>
          </div>
          {tenant?.policy.autonomy === "autonomous" && (
            <Badge tone="ok" dot>no human in the loop</Badge>
          )}
          <div className="topbar-spacer" />

          <button className="btn ghost sm" onClick={() => void refresh()}>Refresh</button>

          {/* Single-tenant deployment: this is a plain label, not a switcher —
              MIDAS is run for one company. See docs/design/DESIGN_BRIEF.md. */}
          <div className="tenant-badge">
            <span className="tenant-name">{tenant?.name ?? "Loading…"}</span>
          </div>
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

          {!tenant && !loadError && <div className="dim">Loading…</div>}

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
