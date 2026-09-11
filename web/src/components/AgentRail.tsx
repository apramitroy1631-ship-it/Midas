import { useState } from "react";
import type { StepEvent } from "../lib/types";
import { Badge, Chips, Json, Meter, duration } from "./ui";

/** Glyph per node, so the rail is scannable without reading labels. */
const GLYPH: Record<string, string> = {
  orchestrate: "◆",
  research: "◈",
  strategy: "▲",
  content: "✎",
  seo: "⌗",
  qa: "✓",
  revise: "↻",
  arbitrate: "⚖",
  publish: "↑",
  analytics: "∿",
  learn: "◉",
};

function nodeTone(step: StepEvent): string {
  if (step.node === "revise" || step.node === "arbitrate") return "revise";
  if (step.node === "qa" && step.output?.passed === false) return "revise";
  return "done";
}

/** One-line gist of a step, so the rail is useful without expanding anything. */
function summarise(step: StepEvent): string {
  const o = step.output ?? {};
  switch (step.node) {
    case "orchestrate":
      return `${o.goal_origin === "self-directed" ? "Chose its own goal" : "Sharpened the goal"} · ${
        (o.channels ?? []).length
      } channels · ${(o.success_criteria ?? []).length} success criteria`;
    case "research":
      return `${(o.key_insights ?? []).length} insights · ${(o.competitors ?? []).length} competitors · market $${
        o.market_size ?? "?"
      }M at ${o.growth_rate ?? "?"}% CAGR`;
    case "strategy":
      return `${(o.objectives ?? []).length} objectives · ${(o.tactics ?? []).length} tactics across ${
        (o.channels ?? []).join(", ") || "—"
      }`;
    case "content":
      return `${(o.assets ?? []).length} assets drafted${
        o.revision_notes && o.revision_notes !== "initial draft" ? " · revised" : ""
      }`;
    case "seo":
      return `${(o.per_asset ?? []).length} assets optimised · ${
        (o.distribution_notes ?? []).length
      } distribution notes`;
    case "qa": {
      const issues = o.issues ?? [];
      const critical = issues.filter((i: any) => i.severity === "critical").length;
      return o.passed
        ? `Passed · safety ${o.brand_safety_score} · alignment ${o.goal_alignment_score}`
        : `Blocked · ${critical} critical, ${issues.length - critical} advisory`;
    }
    case "revise":
      return "QA blocked the draft — sending the specific issues back to the writer";
    case "arbitrate":
      return "Revision budget spent — deciding what can still ship";
    case "publish":
      return "Assets written to the content library";
    case "analytics":
      return `${(o.total_impressions ?? 0).toLocaleString()} projected impressions · ${
        o.overall_ctr ?? "?"
      }% CTR`;
    case "learn":
      return `${(o.insights ?? []).length} insights written back to brand memory`;
    default:
      return "";
  }
}

/* --- node-specific detail panels ----------------------------------------- */

function List({ label, items }: { label: string; items?: string[] }) {
  if (!items?.length) return null;
  return (
    <div style={{ marginBottom: 12 }}>
      <div className="field-label">{label}</div>
      <ul className="list-tight muted">
        {items.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
    </div>
  );
}

function Detail({ step }: { step: StepEvent }) {
  const o = step.output ?? {};

  if (step.node === "orchestrate") {
    return (
      <>
        <div style={{ marginBottom: 12 }}>
          <div className="field-label">Goal</div>
          <div style={{ fontSize: 13.5, fontWeight: 550 }}>{o.goal}</div>
          <div style={{ marginTop: 6 }}>
            <Badge tone={o.goal_origin === "self-directed" ? "info" : "muted"}>
              {o.goal_origin}
            </Badge>
          </div>
        </div>
        <div style={{ marginBottom: 12 }}>
          <div className="field-label">Reasoning</div>
          <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.6 }}>{o.reasoning}</div>
        </div>
        <div style={{ marginBottom: 12 }}>
          <div className="field-label">Channel plan</div>
          {(o.channels ?? []).map((c: any, i: number) => (
            <div key={i} className="row" style={{ padding: "5px 0", alignItems: "flex-start" }}>
              <Badge tone="info">{c.channel}</Badge>
              <span className="mono dim">{Math.round((c.budget_share ?? 0) * 100)}%</span>
              <span className="muted" style={{ fontSize: 12.5 }}>{c.rationale}</span>
            </div>
          ))}
        </div>
        <List label="Research questions delegated" items={o.research_focus} />
        <List label="Success criteria for QA" items={o.success_criteria} />
        <List label="Risk flags" items={o.risk_flags} />
      </>
    );
  }

  if (step.node === "research") {
    return (
      <>
        <dl className="kv" style={{ marginBottom: 14 }}>
          <dt>Market size</dt><dd className="mono">${o.market_size}M</dd>
          <dt>Growth (CAGR)</dt><dd className="mono">{o.growth_rate}%</dd>
          <dt>Audience</dt><dd className="muted">{o.target_audience}</dd>
        </dl>
        <List label="Key insights" items={o.key_insights} />
        <div style={{ marginBottom: 12 }}>
          <div className="field-label">Competitors</div>
          {(o.competitors ?? []).map((c: any, i: number) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 13, fontWeight: 550 }}>{c.name}</div>
              <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.55 }}>{c.positioning}</div>
            </div>
          ))}
        </div>
        <List label="Sources" items={o.sources} />
      </>
    );
  }

  if (step.node === "strategy") {
    return (
      <>
        <div style={{ marginBottom: 12 }}>
          <div className="field-label">Summary</div>
          <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.6 }}>{o.summary}</div>
        </div>
        <List label="Objectives" items={o.objectives} />
        <List label="Tactics" items={o.tactics} />
        <List label="Budget allocation" items={o.budget_allocation} />
      </>
    );
  }

  if (step.node === "content") {
    return (
      <>
        {o.revision_notes && o.revision_notes !== "initial draft" && (
          <div className="banner warn" style={{ marginBottom: 14 }}>
            <span>↻</span>
            <div><strong>Revision notes.</strong> {o.revision_notes}</div>
          </div>
        )}
        {(o.assets ?? []).map((a: any, i: number) => (
          <div className="asset" key={i} style={{ marginBottom: 10 }}>
            <div className="asset-head">
              <Badge tone="info">{a.channel}</Badge>
            </div>
            <div className="asset-headline">{a.headline}</div>
            <div className="asset-body">{a.body}</div>
            <div className="asset-cta">→ {a.call_to_action}</div>
          </div>
        ))}
      </>
    );
  }

  if (step.node === "seo") {
    return (
      <>
        {(o.per_asset ?? []).map((s: any, i: number) => (
          <div key={i} style={{ marginBottom: 14 }}>
            <div className="row" style={{ marginBottom: 6 }}>
              <Badge tone="info">{s.channel}</Badge>
              <span className="mono dim">{s.primary_keyword}</span>
            </div>
            <dl className="kv" style={{ fontSize: 12.5 }}>
              <dt>Meta title</dt><dd>{s.meta_title}</dd>
              <dt>Meta description</dt><dd className="muted">{s.meta_description}</dd>
              <dt>Slug</dt><dd className="mono">/{s.slug}</dd>
            </dl>
            <div style={{ marginTop: 7 }}>
              <Chips items={[...(s.secondary_keywords ?? []), ...(s.hashtags ?? [])]} />
            </div>
          </div>
        ))}
        <List label="Distribution notes" items={o.distribution_notes} />
      </>
    );
  }

  if (step.node === "qa") {
    const issues = o.issues ?? [];
    return (
      <>
        <div className="grid grid-2" style={{ marginBottom: 14 }}>
          <div>
            <div className="field-label">Brand safety</div>
            <div className="row">
              <span className="mono" style={{ fontSize: 17, fontWeight: 600 }}>{o.brand_safety_score}</span>
              <div style={{ flex: 1 }}><Meter value={o.brand_safety_score ?? 0} /></div>
            </div>
          </div>
          <div>
            <div className="field-label">Goal alignment</div>
            <div className="row">
              <span className="mono" style={{ fontSize: 17, fontWeight: 600 }}>{o.goal_alignment_score}</span>
              <div style={{ flex: 1 }}><Meter value={o.goal_alignment_score ?? 0} /></div>
            </div>
          </div>
        </div>
        <div style={{ marginBottom: 14 }}>
          <div className="field-label">Verdict</div>
          <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.6 }}>{o.verdict}</div>
        </div>
        {issues.map((issue: any, i: number) => (
          <div
            key={i}
            style={{
              borderLeft: "2.5px solid " + (issue.severity === "critical" ? "var(--danger)" : "var(--warn)"),
              paddingLeft: 12,
              marginBottom: 12,
            }}
          >
            <div className="row gap-sm" style={{ marginBottom: 4 }}>
              <Badge tone={issue.severity === "critical" ? "danger" : "warn"}>{issue.severity}</Badge>
              <span className="mono dim">{issue.channel}</span>
            </div>
            <div style={{ fontSize: 12.5, lineHeight: 1.55 }}>{issue.issue}</div>
            <div className="muted" style={{ fontSize: 12.5, marginTop: 5, lineHeight: 1.55 }}>
              <strong>Fix:</strong> {issue.fix}
            </div>
          </div>
        ))}
      </>
    );
  }

  if (step.node === "analytics") {
    return (
      <>
        <div className="grid grid-4" style={{ marginBottom: 14 }}>
          <div><div className="field-label">Impressions</div><div className="mono" style={{ fontSize: 16 }}>{(o.total_impressions ?? 0).toLocaleString()}</div></div>
          <div><div className="field-label">Clicks</div><div className="mono" style={{ fontSize: 16 }}>{(o.total_clicks ?? 0).toLocaleString()}</div></div>
          <div><div className="field-label">CTR</div><div className="mono" style={{ fontSize: 16 }}>{o.overall_ctr}%</div></div>
          <div><div className="field-label">Proj. CAC</div><div className="mono" style={{ fontSize: 16 }}>${o.projected_cac_usd}</div></div>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Channel</th><th>Impressions</th><th>Clicks</th><th>CTR</th></tr></thead>
            <tbody>
              {(o.channel_breakdown ?? []).map((c: any, i: number) => (
                <tr key={i} style={{ cursor: "default" }}>
                  <td>{c.channel_name}</td>
                  <td className="mono">{c.impressions.toLocaleString()}</td>
                  <td className="mono">{c.clicks.toLocaleString()}</td>
                  <td className="mono">{c.ctr}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>
    );
  }

  if (step.node === "learn") {
    return (
      <>
        <List label="Insights written to memory" items={o.insights} />
        <List label="Winning angles" items={o.winning_angles} />
        <List label="Angles now marked exhausted" items={o.exhausted_angles} />
        <div>
          <div className="field-label">Suggested next goal</div>
          <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.6 }}>{o.next_goal_suggestion}</div>
        </div>
      </>
    );
  }

  if (!o || (typeof o === "object" && !Object.keys(o).length)) {
    return <div className="dim" style={{ fontSize: 12.5 }}>No structured output for this step.</div>;
  }
  return <Json data={o} />;
}

/* --- the rail ------------------------------------------------------------ */

export function AgentRail({
  steps,
  running,
  error,
}: {
  steps: StepEvent[];
  running: boolean;
  error?: string | null;
}) {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <div className="rail">
      {steps.map((step, i) => {
        const isOpen = open === i;
        const last = i === steps.length - 1 && !running && !error;
        return (
          <div className="rail-step" key={i}>
            <div className="rail-gutter">
              <div className={"rail-node " + nodeTone(step)}>{GLYPH[step.node] ?? "•"}</div>
              {!last && <div className="rail-line" />}
            </div>
            <div className="rail-body">
              {step.node === "revise" ? (
                <div className="revision-banner">
                  <span>↻</span>
                  <div>
                    <strong>Revision cycle {step.revision}.</strong> QA blocked the draft. The
                    specific issues went back to the content agent — no human involved.
                  </div>
                </div>
              ) : (
                <button
                  className={"rail-card" + (isOpen ? " open" : "")}
                  onClick={() => setOpen(isOpen ? null : i)}
                >
                  <div className="rail-card-head">
                    <span className="rail-card-title">{step.label}</span>
                    {step.revision > 0 && step.node === "content" && (
                      <Badge tone="warn">rev {step.revision}</Badge>
                    )}
                    {step.node === "qa" && (
                      <Badge tone={step.output?.passed ? "ok" : "danger"}>
                        {step.output?.passed ? "passed" : "blocked"}
                      </Badge>
                    )}
                    <span className="rail-card-time">{duration(step.elapsed_ms)}</span>
                  </div>
                  <div className="rail-summary">{summarise(step)}</div>
                  {isOpen && (
                    <div className="rail-detail" onClick={(e) => e.stopPropagation()}>
                      <Detail step={step} />
                    </div>
                  )}
                </button>
              )}
            </div>
          </div>
        );
      })}

      {running && (
        <div className="rail-step">
          <div className="rail-gutter">
            <div className="rail-node active">
              <span className="dot pulse" style={{ background: "var(--running)" }} />
            </div>
          </div>
          <div className="rail-body">
            <div className="rail-card" style={{ cursor: "default" }}>
              <div className="rail-summary" style={{ marginTop: 0 }}>
                Agent working…
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="rail-step">
          <div className="rail-gutter">
            <div className="rail-node fail">!</div>
          </div>
          <div className="rail-body">
            <div className="banner danger" style={{ margin: 0 }}>
              <span>✕</span>
              <div><strong>Run failed.</strong> {error}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
