import { useEffect, useMemo, useRef, useState } from "react";
import { api, streamRun } from "../lib/api";
import type { Brand, Connection } from "../lib/types";
import { AgentRail } from "./AgentRail";
import { ChannelIcon } from "./ChannelIcon";
import { Badge } from "./ui";
import type { StepEvent } from "../lib/types";

type Phase = "idle" | "running" | "done" | "error";

const CHANNEL_LABEL: Record<string, string> = { email: "Mail", blog: "Blog", linkedin: "LinkedIn" };

/** Reads intent straight out of the prompt: mentions of linkedin/post steer to
 * LinkedIn, mentions of mail/letter/message/email steer to email, both can fire
 * together, and if neither is mentioned it's ambiguous enough to just generate
 * across all three channels rather than guess wrong. */
function detectChannels(prompt: string): string[] {
  const text = prompt.toLowerCase();
  const wantsLinkedin = /linkedin|\bpost\b/.test(text);
  const wantsEmail = /\bmail\b|\bletter\b|\bmessage\b|\bemail\b/.test(text);
  const channels: string[] = [];
  if (wantsLinkedin) channels.push("linkedin");
  if (wantsEmail) channels.push("email");
  return channels.length ? channels : ["email", "blog", "linkedin"];
}

export function OnDemandModal({
  conn,
  brands,
  defaultBrandId,
  onClose,
  onFinished,
  onOpenAsset,
}: {
  conn: Connection;
  brands: Brand[];
  defaultBrandId: string;
  onClose: () => void;
  onFinished: () => void;
  onOpenAsset?: (id: string) => void;
}) {
  const [brandId, setBrandId] = useState(defaultBrandId);
  const [prompt, setPrompt] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [steps, setSteps] = useState<StepEvent[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [opening, setOpening] = useState(false);
  const abort = useRef<AbortController | null>(null);

  const detected = useMemo(() => detectChannels(prompt), [prompt]);
  const running = phase === "running";

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && !running && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, running]);

  async function generate() {
    if (!prompt.trim() || !brandId) return;
    const channels = detectChannels(prompt);
    setSteps([]);
    setResult(null);
    setError(null);
    setPhase("running");
    abort.current = new AbortController();

    try {
      await streamRun(
        conn,
        {
          brand_id: brandId,
          goal: prompt.trim(),
          target_audience: null,
          budget: 0,
          trigger: "manual",
          channels,
        },
        async (event, data) => {
          if (event === "step") setSteps((s) => [...s, data]);
          else if (event === "done") {
            setResult(data);
            setPhase(data.status === "failed" ? "error" : "done");
            if (data.error) setError(data.error);
            onFinished();
            if (data.status !== "failed") await openResult(data.run_id, channels);
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

  /** One channel: skip straight to the editor, same fast path as New Campaign's
   * mail-only run. Multiple channels: land in the library instead of picking
   * one arbitrarily to open. */
  async function openResult(runId: string, channels: string[]) {
    if (channels.length !== 1 || !onOpenAsset) return;
    setOpening(true);
    try {
      const fresh = await api.assets(conn, brandId);
      const created = fresh.find((a) => a.run_id === runId && a.channel === channels[0]);
      if (created) {
        onOpenAsset(created.id);
        onClose();
      }
    } catch {
      /* the in-modal outcome still shows the run */
    } finally {
      setOpening(false);
    }
  }

  function stop() {
    abort.current?.abort();
    setPhase("idle");
  }

  return (
    <>
      <div className="scrim" onClick={() => !running && onClose()} />
      <div className="ondemand-backdrop">
        <div className="ondemand-modal">
          <div className="ondemand-head">
            <div>
              <h3 className="card-title">✨ On-demand content</h3>
              <p className="card-sub">Describe what you want, the pipeline figures out the rest.</p>
            </div>
            <span className="spacer" />
            <button className="btn ghost sm" onClick={onClose} disabled={running}>Close</button>
          </div>

          <div className="ondemand-body">
            <div className="field-label" style={{ marginBottom: 6 }}>Brand</div>
            <select
              className="select"
              style={{ marginBottom: 14 }}
              value={brandId}
              onChange={(e) => setBrandId(e.target.value)}
              disabled={running}
            >
              {brands.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>

            <div className="field-label" style={{ marginBottom: 6 }}>Prompt</div>
            <textarea
              className="textarea"
              style={{ minHeight: 110 }}
              placeholder="e.g. Write a LinkedIn post announcing our new integration, and a follow-up email for existing customers"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={running}
              autoFocus
            />

            <div className="row wrap gap-sm" style={{ marginTop: 10 }}>
              <span className="field-label" style={{ margin: 0, alignSelf: "center" }}>Will generate</span>
              {detected.map((c) => (
                <Badge key={c} tone="info">
                  <ChannelIcon channel={c} size={12} /> {CHANNEL_LABEL[c]}
                </Badge>
              ))}
            </div>

            {(steps.length > 0 || running) && (
              <div style={{ marginTop: 16 }}>
                <div className="field-label" style={{ marginBottom: 8 }}>Pipeline</div>
                <div style={{ maxHeight: 260, overflowY: "auto" }}>
                  <AgentRail steps={steps} running={running} error={error} />
                </div>
              </div>
            )}

            {error && phase === "error" && (
              <div className="banner danger" style={{ marginTop: 14 }}>
                <span>✕</span>
                <div>{error}</div>
              </div>
            )}

            {result && result.status !== "failed" && detected.length > 1 && (
              <div className="banner info" style={{ marginTop: 14 }}>
                <span>ⓘ</span>
                <div>
                  Done — {result.asset_count} asset(s) generated. Find them in the Content Library.
                </div>
              </div>
            )}
          </div>

          <div className="ondemand-foot">
            <button className="btn ghost" onClick={onClose} disabled={running}>Cancel</button>
            <button
              className={"btn " + (running ? "danger" : "primary")}
              onClick={running ? stop : generate}
              disabled={!running && (!prompt.trim() || !brandId || opening)}
            >
              {running ? "■  Stop" : opening ? "Opening…" : "✨  Generate"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
