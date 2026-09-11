import { useRef, useState } from "react";
import { AgentRail } from "../components/AgentRail";
import { Badge, Card, Empty, Field, StatusBadge, duration } from "../components/ui";
import { streamRun } from "../lib/api";
import type { Brand, Connection, StepEvent, Tenant } from "../lib/types";

type Phase = "idle" | "running" | "done" | "error";

export function Launch({
  conn,
  tenant,
  brands,
  onFinished,
}: {
  conn: Connection;
  tenant: Tenant;
  brands: Brand[];
  onFinished: () => void;
}) {
  const [brandId, setBrandId] = useState(brands[0]?.id ?? "");
  const [goal, setGoal] = useState("");
  const [audience, setAudience] = useState("");
  const [budget, setBudget] = useState("8000");

  const [phase, setPhase] = useState<Phase>("idle");
  const [steps, setSteps] = useState<StepEvent[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);

  const brand = brands.find((b) => b.id === brandId);
  const autonomous = tenant.policy.autonomy === "autonomous" && tenant.policy.auto_publish;

  async function run() {
    setSteps([]);
    setResult(null);
    setError(null);
    setMeta(null);
    setPhase("running");
    abort.current = new AbortController();

    try {
      await streamRun(
        conn,
        {
          brand_id: brandId,
          goal: goal.trim() || null,
          target_audience: audience.trim() || null,
          budget: Number(budget) || 0,
          trigger: "manual",
        },
        (event, data) => {
          if (event === "start") setMeta(data);
          else if (event === "step") setSteps((s) => [...s, data]);
          else if (event === "done") {
            setResult(data);
            setPhase(data.status === "failed" ? "error" : "done");
            if (data.error) setError(data.error);
            onFinished();
          } else if (event === "error") {
            setError(data.message);
            setPhase("error");
          }
        },
        abort.current.signal
      );
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        setPhase("idle");
        return;
      }
      setError(err instanceof Error ? err.message : String(err));
      setPhase("error");
    }
  }

  function stop() {
    abort.current?.abort();
    setPhase("idle");
  }

  if (!brands.length) {
    return (
      <Empty
        icon="◇"
        title="No brands yet"
        text="The agents need a brand to work on — its voice, USP, and content restrictions are what the whole pipeline is bound by. Add one under Brands first."
      />
    );
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(280px, 320px) 1fr", gap: 18, alignItems: "start" }}>
      <div className="col">
        <Card title="Campaign brief" sub="Everything here is optional except the brand.">
          <Field label="Brand">
            <select className="select" value={brandId} onChange={(e) => setBrandId(e.target.value)}>
              {brands.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </Field>

          <Field
            label="Campaign goal"
            hint="Leave blank and the Campaign Director reads brand memory and picks the goal itself."
          >
            <textarea
              className="textarea"
              value={goal}
              placeholder="e.g. Drive demo requests for the Q4 launch"
              onChange={(e) => setGoal(e.target.value)}
            />
          </Field>

          <Field label="Audience override" hint="Optional. The Director sharpens this either way.">
            <input
              className="input"
              value={audience}
              placeholder={brand?.target_audience ?? ""}
              onChange={(e) => setAudience(e.target.value)}
            />
          </Field>

          <Field label="Budget (USD)">
            <input
              className="input mono"
              value={budget}
              onChange={(e) => setBudget(e.target.value.replace(/[^\d.]/g, ""))}
            />
          </Field>

          <button
            className={"btn block " + (phase === "running" ? "danger" : "primary")}
            onClick={phase === "running" ? stop : run}
            disabled={!brandId}
            style={{ marginTop: 4 }}
          >
            {phase === "running" ? "■  Stop run" : "▶  Launch autonomous run"}
          </button>
        </Card>

        <Card title="Autonomy">
          <div className="col gap-sm" style={{ fontSize: 12.5 }}>
            <div className="row">
              <Badge tone={autonomous ? "ok" : "warn"} dot>
                {autonomous ? "fully autonomous" : "review required"}
              </Badge>
            </div>
            <p className="muted" style={{ margin: "6px 0 0", lineHeight: 1.6 }}>
              {autonomous
                ? "QA failures loop back to the writer instead of stopping for a person. Content publishes on a clean pass with no human approval."
                : "The agents run identically, but finished content parks in the review queue instead of publishing."}
            </p>
            <div className="row dim" style={{ marginTop: 8, fontSize: 12 }}>
              <span>Revision budget</span>
              <span className="spacer" />
              <span className="mono">{tenant.policy.max_revision_cycles} cycles</span>
            </div>
            <div className="row dim" style={{ fontSize: 12 }}>
              <span>Runs this period</span>
              <span className="spacer" />
              <span className="mono">
                {tenant.usage.runs_this_period} / {tenant.limits.monthly_run_quota}
              </span>
            </div>
          </div>
        </Card>
      </div>

      <div className="col">
        {meta && (
          <Card>
            <div className="row wrap">
              <span className="mono dim">run {meta.run_id?.slice(0, 8)}</span>
              <Badge tone={meta.goal_origin === "self-directed" ? "info" : "muted"}>
                {meta.goal_origin}
              </Badge>
              <span className="spacer" />
              {result ? (
                <>
                  <StatusBadge status={result.status} />
                  <span className="mono dim">{duration(result.duration_ms)}</span>
                </>
              ) : (
                <Badge tone="info" dot>running</Badge>
              )}
            </div>
          </Card>
        )}

        {phase === "idle" && !steps.length ? (
          <Card>
            <Empty
              icon="◆"
              title="Ready to run"
              text="Eleven agent steps: the Director plans and delegates, specialists research, strategise, write, optimise and review, and QA decides whether it ships. A blocked draft comes back here as a revision cycle, not a request for your approval."
            />
          </Card>
        ) : (
          <Card title="Agent pipeline" sub={`${steps.length} steps`}>
            <AgentRail steps={steps} running={phase === "running"} error={error} />
          </Card>
        )}

        {result && result.status !== "failed" && (
          <Card title="Outcome">
            <div className="grid grid-4">
              <div>
                <div className="field-label">Assets</div>
                <div className="mono" style={{ fontSize: 19 }}>{result.asset_count}</div>
              </div>
              <div>
                <div className="field-label">Revisions</div>
                <div className="mono" style={{ fontSize: 19 }}>{result.revisions}</div>
              </div>
              <div>
                <div className="field-label">Brand safety</div>
                <div className="mono" style={{ fontSize: 19 }}>{result.brand_safety_score ?? "—"}</div>
              </div>
              <div>
                <div className="field-label">Goal alignment</div>
                <div className="mono" style={{ fontSize: 19 }}>{result.goal_alignment_score ?? "—"}</div>
              </div>
            </div>
            {!!result.dropped_channels?.length && (
              <div className="banner warn" style={{ marginTop: 14, marginBottom: 0 }}>
                <span>⚖</span>
                <div>
                  <strong>Arbitration.</strong> The revision budget ran out with issues still open, so
                  these channels were dropped and the rest shipped: {result.dropped_channels.join(", ")}.
                </div>
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
