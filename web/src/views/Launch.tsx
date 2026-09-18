import { useEffect, useRef, useState } from "react";
import { AgentRail } from "../components/AgentRail";
import { ChannelIcon } from "../components/ChannelIcon";
import { DateRangePicker } from "../components/DateRangePicker";
import { OnDemandModal } from "../components/OnDemandModal";
import { Badge, Card, Empty, Field, StatusBadge, ToggleRow, duration } from "../components/ui";
import { api, streamRun } from "../lib/api";
import type { Brand, Connection, Schedule, StepEvent, Tenant } from "../lib/types";

const WEEKDAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

type Phase = "idle" | "running" | "done" | "error";

const CHANNEL_OPTIONS = [
  { id: "email", label: "Mail" },
  { id: "blog", label: "Blog" },
  { id: "linkedin", label: "LinkedIn" },
];

const WEEKDAY_OPTIONS = [
  { id: 0, label: "Mon" },
  { id: 1, label: "Tue" },
  { id: 2, label: "Wed" },
  { id: 3, label: "Thu" },
  { id: 4, label: "Fri" },
  { id: 5, label: "Sat" },
  { id: 6, label: "Sun" },
];

function todayKey(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function Launch({
  conn,
  tenant,
  brands,
  onFinished,
  onOpenAsset,
}: {
  conn: Connection;
  tenant: Tenant;
  brands: Brand[];
  onFinished: () => void;
  onOpenAsset?: (id: string) => void;
}) {
  const [brandId, setBrandId] = useState(brands[0]?.id ?? "");
  const [goal, setGoal] = useState("");
  const [audience, setAudience] = useState("");
  const [budget, setBudget] = useState("8000");
  const [channels, setChannels] = useState<string[]>([]); // empty = let the Director choose

  // Scheduling: keeps the pipeline from firing outside what an operator
  // explicitly asked for. Off = runs now, on demand. On = defers to a
  // recurring sweep that only fires on the chosen weekdays within the range.
  const [scheduling, setScheduling] = useState(false);
  const [schedStart, setSchedStart] = useState("");
  const [schedEnd, setSchedEnd] = useState("");
  const [weekdays, setWeekdays] = useState<number[]>([]);
  const [scheduleSaving, setScheduleSaving] = useState(false);
  const [scheduleMsg, setScheduleMsg] = useState<string | null>(null);

  const [phase, setPhase] = useState<Phase>("idle");
  const [steps, setSteps] = useState<StepEvent[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [openingAsset, setOpeningAsset] = useState(false);
  const [onDemandOpen, setOnDemandOpen] = useState(false);
  const abort = useRef<AbortController | null>(null);

  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const loadSchedules = () => api.schedules(conn).then(setSchedules).catch(() => {});
  useEffect(() => { void loadSchedules(); }, [conn]);

  async function cancelSchedule(id: string) {
    await api.deleteSchedule(conn, id);
    void loadSchedules();
  }

  const brand = brands.find((b) => b.id === brandId);
  const autonomous = tenant.policy.autonomy === "autonomous" && tenant.policy.auto_publish;
  const mailOnly = channels.length === 1 && channels[0] === "email";

  function toggleChannel(id: string) {
    setChannels((cs) => (cs.includes(id) ? cs.filter((c) => c !== id) : [...cs, id]));
  }

  function toggleWeekday(id: number) {
    setWeekdays((ws) => (ws.includes(id) ? ws.filter((w) => w !== id) : [...ws, id]));
  }

  async function createSchedule() {
    if (!brandId || !schedStart || !schedEnd || !weekdays.length) return;
    setScheduleSaving(true);
    setScheduleMsg(null);
    try {
      await api.createSchedule(conn, {
        brand_id: brandId,
        goal: goal.trim() || null,
        target_audience: audience.trim() || null,
        budget: Number(budget) || 0,
        channels: channels.length ? channels : null,
        start_date: schedStart,
        end_date: schedEnd,
        weekdays,
      });
      setScheduleMsg("Scheduled. It'll run automatically on the days you picked — nothing fires until then.");
      setWeekdays([]);
      setSchedStart("");
      setSchedEnd("");
      onFinished();
      void loadSchedules();
    } catch (err) {
      setScheduleMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setScheduleSaving(false);
    }
  }

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
          channels: channels.length ? channels : null,
        },
        (event, data) => {
          if (event === "start") setMeta(data);
          else if (event === "step") setSteps((s) => [...s, data]);
          else if (event === "done") {
            setResult(data);
            setPhase(data.status === "failed" ? "error" : "done");
            if (data.error) setError(data.error);
            onFinished();
            if (mailOnly && data.status !== "failed" && onOpenAsset) void openMailResult(data.run_id);
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

  /** The "only Mail" fast path: skip the outcome summary and go straight to
   * editing the email that just got written. */
  async function openMailResult(runId: string) {
    setOpeningAsset(true);
    try {
      const fresh = await api.assets(conn, brandId);
      const created = fresh.find((a) => a.run_id === runId && a.channel === "email");
      if (created) onOpenAsset?.(created.id);
    } catch {
      /* the outcome card below still shows the run — not a dead end */
    } finally {
      setOpeningAsset(false);
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
    <div style={{ display: "grid", gridTemplateColumns: "minmax(360px, 440px) 1fr", gap: 18, alignItems: "start" }}>
      <div className="col">
        <Card title="Campaign brief" sub="Everything here is optional except the brand.">
          <button
            type="button"
            className="ondemand-trigger"
            onClick={() => setOnDemandOpen(true)}
          >
            <span>✨ On-demand content</span>
            <span className="ondemand-trigger-sub">Write a prompt, skip the form — the pipeline runs from that instead</span>
          </button>

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

          <Field
            label="Channels"
            hint={
              mailOnly
                ? "Just an email — this generates live and opens straight in the content editor when it's ready, no summary screen in between."
                : "Leave on \"All\" and the Director picks 2–4 channels itself. Pick specific ones to constrain it."
            }
          >
            <div className="row wrap gap-sm">
              <button
                type="button"
                className={"chip-toggle" + (channels.length === 0 ? " active" : "")}
                onClick={() => setChannels([])}
              >
                All channels
              </button>
              {CHANNEL_OPTIONS.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className={"chip-toggle" + (channels.includes(c.id) ? " active" : "")}
                  onClick={() => toggleChannel(c.id)}
                >
                  <ChannelIcon channel={c.id} size={13} /> {c.label}
                </button>
              ))}
            </div>
          </Field>

          <div className="field" style={{ borderTop: "1px solid var(--border-soft)", paddingTop: 13 }}>
            <ToggleRow
              title="Schedule this campaign"
              desc="Off = runs now, on demand. On = it sits idle and only fires automatically on the days you pick below — nothing runs outside that."
              on={scheduling}
              onChange={(v) => { setScheduling(v); setScheduleMsg(null); }}
            />
          </div>

          {scheduling && (
            <Field
              label="Date range & days"
              hint="Pick a range from today onward, then which weekdays inside it the pipeline should run on."
            >
              <DateRangePicker
                from={schedStart}
                to={schedEnd}
                minDate={todayKey()}
                onChange={(f, t) => { setSchedStart(f); setSchedEnd(t); }}
              />
              <div className="row wrap gap-sm" style={{ marginTop: 10 }}>
                {WEEKDAY_OPTIONS.map((w) => (
                  <button
                    key={w.id}
                    type="button"
                    className={"chip-toggle" + (weekdays.includes(w.id) ? " active" : "")}
                    onClick={() => toggleWeekday(w.id)}
                  >
                    {w.label}
                  </button>
                ))}
              </div>
            </Field>
          )}

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

          {scheduleMsg && (
            <div className={"banner " + (scheduleMsg.startsWith("Scheduled") ? "info" : "danger")} style={{ marginBottom: 12 }}>
              <span>{scheduleMsg.startsWith("Scheduled") ? "ⓘ" : "✕"}</span>
              <div>{scheduleMsg}</div>
            </div>
          )}

          <button
            className={"btn block " + (phase === "running" ? "danger" : "primary")}
            onClick={scheduling ? createSchedule : phase === "running" ? stop : run}
            disabled={
              !brandId ||
              openingAsset ||
              (scheduling && (!schedStart || !schedEnd || !weekdays.length || scheduleSaving))
            }
            style={{ marginTop: 4 }}
          >
            {scheduling
              ? scheduleSaving
                ? "Saving…"
                : "📅  Schedule campaign"
              : phase === "running"
              ? "■  Stop run"
              : openingAsset
              ? "Opening your email…"
              : mailOnly
              ? "✉  Generate email now"
              : "▶  Launch autonomous run"}
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
        {schedules.length > 0 && (
          <Card title="Scheduled campaigns" sub={`${schedules.length} active — nothing else runs on its own`}>
            <div className="col gap-sm">
              {schedules.map((s) => (
                <div key={s.id} className="row wrap" style={{ fontSize: 12.5, alignItems: "center" }}>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div className="truncate" style={{ fontWeight: 600 }}>{s.goal || "Director picks the goal"}</div>
                    <div className="dim mono" style={{ fontSize: 11 }}>
                      {s.brand_name} · {s.start_date} → {s.end_date} · {s.weekdays.map((d) => WEEKDAY_SHORT[d]).join(", ")}
                    </div>
                  </div>
                  {s.active ? <Badge tone="ok" dot>active</Badge> : <Badge tone="muted">paused</Badge>}
                  <button className="btn ghost sm" onClick={() => void cancelSchedule(s.id)}>Cancel</button>
                </div>
              ))}
            </div>
          </Card>
        )}

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

      {onDemandOpen && (
        <OnDemandModal
          conn={conn}
          brands={brands}
          defaultBrandId={brandId}
          onClose={() => setOnDemandOpen(false)}
          onFinished={onFinished}
          onOpenAsset={onOpenAsset}
        />
      )}
    </div>
  );
}
