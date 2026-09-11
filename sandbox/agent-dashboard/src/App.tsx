import { useRef, useState } from "react";
import { streamSSE } from "./sse";

type BackendKey = "kartik" | "shivay";

type TimelineEntry = {
  id: number;
  node: string;
  label: string;
  status: "running" | "done";
  output?: unknown;
  ts: string;
};

type RunStatus = "idle" | "running" | "completed" | "failed" | "error";

const ACCENTS: Record<BackendKey, { color: string; dim: string; name: string }> = {
  kartik: { color: "var(--kartik)", dim: "var(--kartik-dim)", name: "Kartik Pipeline" },
  shivay: { color: "var(--shivay)", dim: "var(--shivay-dim)", name: "Shivay Pipeline" },
};

function nowStamp() {
  return new Date().toLocaleTimeString([], { hour12: false });
}

export default function App() {
  const [backend, setBackend] = useState<BackendKey>("kartik");

  // connection config — editable so the team can point at whatever Railway URL is live
  const [kartikUrl, setKartikUrl] = useState("http://localhost:8000");
  const [shivayUrl, setShivayUrl] = useState("http://localhost:8080");

  // shared campaign-brief fields
  const [brandName, setBrandName] = useState("Acme Robotics");
  const [industry, setIndustry] = useState("B2B SaaS / Robotics");
  const [tone, setTone] = useState("Confident, plain-spoken, no jargon");
  const [usp, setUsp] = useState("Cuts warehouse pick times by 40%");
  const [goal, setGoal] = useState("Drive signups for the Q4 product launch webinar");
  const [targetAudience, setTargetAudience] = useState("Ops leaders at mid-market logistics companies");
  const [budget, setBudget] = useState("5000");
  const [keyword, setKeyword] = useState("warehouse automation software");

  const [status, setStatus] = useState<RunStatus>("idle");
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [finalResult, setFinalResult] = useState<unknown>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const idCounter = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const accent = ACCENTS[backend];

  function resetRun() {
    setTimeline([]);
    setFinalResult(null);
    setErrorMsg(null);
    setExpanded(null);
    idCounter.current = 0;
  }

  function pushEntry(node: string, label: string, output: unknown) {
    idCounter.current += 1;
    setTimeline((t) => [
      ...t,
      { id: idCounter.current, node, label, status: "done", output, ts: nowStamp() },
    ]);
  }

  async function runKartik() {
    const base = kartikUrl.replace(/\/$/, "");

    // Step 1 — create a throwaway test brand (Kartik's pipeline requires one)
    pushEntry("setup", "Create test brand", { name: brandName });
    const brandRes = await fetch(`${base}/brands`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: brandName,
        description: `${brandName} — ${industry}`,
        industry,
        tone,
        usp,
        target_audience: targetAudience,
        brand_guidelines: { visual_style: tone, preferred_channels: ["linkedin", "email"], content_restrictions: [] },
        latest_insights: [],
      }),
    });
    if (!brandRes.ok) throw new Error(`Brand creation failed: ${brandRes.status}`);
    const brand = await brandRes.json();
    const brandId = brand.id;

    // Step 2 — stream the campaign run
    await streamSSE(
      `${base}/brands/${brandId}/campaigns/stream`,
      { brand_id: brandId, goal, target_audience: targetAudience, budget: Number(budget) },
      (event, data) => {
        if (event === "node_complete") {
          pushEntry(data.node, data.label, data.output);
        } else if (event === "done") {
          setFinalResult(data.result);
          setStatus(data.status === "failed" ? "failed" : "completed");
        } else if (event === "error") {
          setErrorMsg(data.message);
          setStatus("error");
        }
      },
      abortRef.current?.signal
    );
  }

  async function runShivay() {
    const base = shivayUrl.replace(/\/$/, "");
    await streamSSE(
      `${base}/campaign/stream`,
      {
        keyword,
        businessName: brandName,
        businessDescription: `${brandName} — ${industry}. ${usp}`,
        targetAudience,
      },
      (event, data) => {
        if (event === "node_complete") {
          pushEntry(data.node, data.label, data.output);
        } else if (event === "done") {
          setFinalResult(data.result);
          setStatus("completed");
        } else if (event === "error") {
          setErrorMsg(data.message);
          setStatus("error");
        }
      },
      abortRef.current?.signal
    );
  }

  async function handleRun() {
    resetRun();
    setStatus("running");
    abortRef.current = new AbortController();
    try {
      if (backend === "kartik") await runKartik();
      else await runShivay();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
      setStatus("error");
    }
  }

  function handleStop() {
    abortRef.current?.abort();
    setStatus("idle");
  }

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div style={styles.brandmark}>
          <span style={styles.brandmarkDot} />
          PIPELINE BENCH
        </div>
        <nav style={styles.tabs}>
          {(Object.keys(ACCENTS) as BackendKey[]).map((k) => (
            <button
              key={k}
              onClick={() => {
                setBackend(k);
                resetRun();
                setStatus("idle");
              }}
              style={{
                ...styles.tab,
                borderColor: backend === k ? ACCENTS[k].color : "var(--border)",
                color: backend === k ? ACCENTS[k].color : "var(--text-muted)",
              }}
            >
              {ACCENTS[k].name}
            </button>
          ))}
        </nav>
      </header>

      <div style={styles.body}>
        <aside style={styles.sidebar}>
          <Section title="Backend URL">
            <input
              style={styles.input}
              value={backend === "kartik" ? kartikUrl : shivayUrl}
              onChange={(e) =>
                backend === "kartik" ? setKartikUrl(e.target.value) : setShivayUrl(e.target.value)
              }
              placeholder="https://your-railway-app.up.railway.app"
            />
          </Section>

          <Section title="Campaign brief">
            <Field label="Brand / business name">
              <input style={styles.input} value={brandName} onChange={(e) => setBrandName(e.target.value)} />
            </Field>
            <Field label="Industry">
              <input style={styles.input} value={industry} onChange={(e) => setIndustry(e.target.value)} />
            </Field>
            <Field label="Tone">
              <input style={styles.input} value={tone} onChange={(e) => setTone(e.target.value)} />
            </Field>
            <Field label="USP">
              <input style={styles.input} value={usp} onChange={(e) => setUsp(e.target.value)} />
            </Field>
            <Field label="Target audience">
              <input
                style={styles.input}
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
              />
            </Field>

            {backend === "kartik" ? (
              <>
                <Field label="Campaign goal">
                  <input style={styles.input} value={goal} onChange={(e) => setGoal(e.target.value)} />
                </Field>
                <Field label="Budget ($)">
                  <input style={styles.input} value={budget} onChange={(e) => setBudget(e.target.value)} />
                </Field>
              </>
            ) : (
              <Field label="Target keyword">
                <input style={styles.input} value={keyword} onChange={(e) => setKeyword(e.target.value)} />
              </Field>
            )}
          </Section>

          <button
            onClick={status === "running" ? handleStop : handleRun}
            style={{
              ...styles.runButton,
              borderColor: accent.color,
              color: status === "running" ? "var(--error)" : accent.color,
            }}
          >
            {status === "running" ? "■ STOP" : "▸ RUN CAMPAIGN"}
          </button>

          <div style={styles.statusLine}>
            <StatusDot status={status} />
            <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text-muted)" }}>
              {status.toUpperCase()}
            </span>
          </div>
        </aside>

        <main style={styles.main}>
          <div style={styles.railHeader}>
            <span style={{ color: "var(--text-muted)", fontSize: 12, letterSpacing: 0.3 }}>
              AGENT TIMELINE
            </span>
            <span style={{ color: "var(--text-dim)", fontSize: 12, fontFamily: "var(--mono)" }}>
              {timeline.length} step{timeline.length === 1 ? "" : "s"}
            </span>
          </div>

          <div style={styles.rail}>
            {timeline.length === 0 && status === "idle" && (
              <div style={styles.emptyState}>
                Configure the brief on the left, then run the campaign to watch each agent complete in
                real time.
              </div>
            )}

            {timeline.map((entry, i) => (
              <div key={entry.id} style={styles.railItem}>
                <div style={styles.railGutter}>
                  <div style={{ ...styles.railDot, background: accent.color }} />
                  {i < timeline.length - 1 && <div style={styles.railLine} />}
                </div>
                <button
                  style={styles.railCard}
                  onClick={() => setExpanded(expanded === entry.id ? null : entry.id)}
                >
                  <div style={styles.railCardHead}>
                    <span style={{ fontFamily: "var(--mono)", fontSize: 13 }}>{entry.label}</span>
                    <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-dim)" }}>
                      {entry.ts}
                    </span>
                  </div>
                  {expanded === entry.id && (
                    <pre style={styles.output}>{JSON.stringify(entry.output, null, 2)}</pre>
                  )}
                </button>
              </div>
            ))}

            {status === "running" && (
              <div style={styles.railItem}>
                <div style={styles.railGutter}>
                  <div style={{ ...styles.railDot, background: "var(--running)", animation: "pulse 1.2s infinite" }} />
                </div>
                <div style={{ ...styles.railCard, color: "var(--text-muted)", fontFamily: "var(--mono)", fontSize: 13 }}>
                  waiting on next agent…
                </div>
              </div>
            )}

            {errorMsg && (
              <div style={{ ...styles.railCard, borderColor: "var(--error)", color: "var(--error)", marginTop: 8 }}>
                {errorMsg}
              </div>
            )}
          </div>

          {finalResult != null && (
            <div style={styles.resultPanel}>
              <div style={styles.railHeader}>
                <span style={{ color: "var(--text-muted)", fontSize: 12 }}>FINAL RESULT</span>
              </div>
              <pre style={styles.output}>{JSON.stringify(finalResult, null, 2)}</pre>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={styles.sectionTitle}>{title}</div>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "block", marginBottom: 10 }}>
      <div style={styles.fieldLabel}>{label}</div>
      {children}
    </label>
  );
}

function StatusDot({ status }: { status: RunStatus }) {
  const color =
    status === "running"
      ? "var(--running)"
      : status === "completed"
      ? "var(--done)"
      : status === "failed" || status === "error"
      ? "var(--error)"
      : "var(--idle)";
  return <span style={{ width: 8, height: 8, borderRadius: "50%", background: color, display: "inline-block" }} />;
}

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: "100vh", display: "flex", flexDirection: "column" },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "16px 24px",
    borderBottom: "1px solid var(--border)",
    flexWrap: "wrap",
    gap: 12,
  },
  brandmark: {
    fontFamily: "var(--mono)",
    fontSize: 13,
    letterSpacing: 1.5,
    color: "var(--text)",
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  brandmarkDot: { width: 8, height: 8, background: "var(--running)", display: "inline-block" },
  tabs: { display: "flex", gap: 8 },
  tab: {
    background: "transparent",
    border: "1px solid var(--border)",
    padding: "8px 14px",
    fontSize: 13,
    fontFamily: "var(--sans)",
    cursor: "pointer",
  },
  body: { flex: 1, display: "flex", minHeight: 0 },
  sidebar: {
    width: 300,
    flexShrink: 0,
    borderRight: "1px solid var(--border)",
    padding: 20,
    overflowY: "auto",
  },
  sectionTitle: {
    fontSize: 11,
    letterSpacing: 0.5,
    color: "var(--text-dim)",
    marginBottom: 10,
    fontFamily: "var(--mono)",
  },
  fieldLabel: { fontSize: 12, color: "var(--text-muted)", marginBottom: 4 },
  input: {
    width: "100%",
    background: "var(--panel-raised)",
    border: "1px solid var(--border)",
    color: "var(--text)",
    padding: "8px 10px",
    fontSize: 13,
    fontFamily: "var(--sans)",
  },
  runButton: {
    width: "100%",
    background: "var(--panel-raised)",
    border: "1px solid",
    padding: "10px 0",
    fontFamily: "var(--mono)",
    fontSize: 13,
    letterSpacing: 0.5,
    cursor: "pointer",
    marginTop: 4,
  },
  statusLine: { display: "flex", alignItems: "center", gap: 8, marginTop: 12 },
  main: { flex: 1, padding: 24, overflowY: "auto" },
  railHeader: { display: "flex", justifyContent: "space-between", marginBottom: 14 },
  rail: { display: "flex", flexDirection: "column" },
  railItem: { display: "flex", gap: 12 },
  railGutter: { display: "flex", flexDirection: "column", alignItems: "center", width: 12 },
  railDot: { width: 10, height: 10, borderRadius: "50%", flexShrink: 0, marginTop: 6 },
  railLine: { width: 1, flex: 1, background: "var(--border)", minHeight: 24 },
  railCard: {
    flex: 1,
    background: "var(--panel)",
    border: "1px solid var(--border-soft)",
    padding: "10px 14px",
    marginBottom: 10,
    textAlign: "left",
    cursor: "pointer",
    color: "var(--text)",
    width: "100%",
  },
  railCardHead: { display: "flex", justifyContent: "space-between" },
  output: {
    marginTop: 10,
    fontFamily: "var(--mono)",
    fontSize: 12,
    color: "var(--text-muted)",
    whiteSpace: "pre-wrap",
    maxHeight: 300,
    overflowY: "auto",
  },
  emptyState: {
    color: "var(--text-dim)",
    fontSize: 13,
    padding: "40px 0",
    maxWidth: 420,
    lineHeight: 1.6,
  },
  resultPanel: { marginTop: 28, borderTop: "1px solid var(--border)", paddingTop: 20 },
};
