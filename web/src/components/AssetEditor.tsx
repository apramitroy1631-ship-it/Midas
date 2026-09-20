import { useRef, useState } from "react";
import { ChannelIcon } from "./ChannelIcon";
import { Drawer } from "./ui";
import { api } from "../lib/api";
import { assetToOutlookHtml, downloadFile, toRtf } from "../lib/download";
import type { Asset, Connection } from "../lib/types";

type Tab = "html" | "rich" | "plain";

/** Plain text only matters where a client might not render HTML at all
 * (email/Outlook). LinkedIn and blog content is always posted somewhere
 * that renders rich formatting, so a plain-text export is just clutter. */
function tabsFor(channel: string): Tab[] {
  return channel.toLowerCase() === "linkedin" || channel.toLowerCase() === "blog"
    ? ["html", "rich"]
    : ["html", "rich", "plain"];
}

const TAB_LABEL: Record<Tab, string> = { html: "HTML", rich: "Rich Text", plain: "Plain Text" };

function plainOf(a: Asset): string {
  return [a.headline, a.body, a.call_to_action].filter(Boolean).join("\n\n");
}

function stripHtml(html: string): string {
  const div = document.createElement("div");
  div.innerHTML = html;
  return div.innerText;
}

/** Best-effort split of freeform edited text back into the asset's actual
 * fields (first paragraph = headline, last = CTA, middle = body). Only
 * fields we're confident about are included, so a one-paragraph edit just
 * updates the body rather than blanking the headline/CTA. */
function splitParts(text: string): Partial<Pick<Asset, "headline" | "body" | "call_to_action">> {
  const parts = text.split(/\n{2,}/).map((s) => s.trim()).filter(Boolean);
  if (parts.length >= 3) {
    return { headline: parts[0], body: parts.slice(1, -1).join("\n\n"), call_to_action: parts[parts.length - 1] };
  }
  if (parts.length === 2) return { headline: parts[0], body: parts[1] };
  if (parts.length === 1) return { body: parts[0] };
  return {};
}

/**
 * A first pass at the "export as HTML / Rich Text / Plain Text for Outlook"
 * goal — raw-source editing rather than a full WYSIWYG engine (that's a
 * much bigger build; see the stored MIDAS email-output-goal memory for the
 * ultimate target). Rich Text here is a real contentEditable surface with
 * basic formatting, downloaded as a plain-text-backed .rtf — Outlook opens
 * it fine, it just won't carry bold/italic through yet.
 */
export function AssetEditor({
  asset,
  conn,
  onClose,
  onSaved,
}: {
  asset: Asset;
  conn: Connection;
  onClose: () => void;
  onSaved?: () => void;
}) {
  const availableTabs = tabsFor(asset.channel);
  const [tab, setTab] = useState<Tab>("html");
  const [current, setCurrent] = useState(asset);
  const [html, setHtml] = useState(() => assetToOutlookHtml(asset.headline, asset.body, asset.call_to_action));
  const [plain, setPlain] = useState(() => plainOf(asset));
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const richRef = useRef<HTMLDivElement>(null);

  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [regenerating, setRegenerating] = useState(false);
  const [regenError, setRegenError] = useState<string | null>(null);

  async function regenerate() {
    if (!feedback.trim()) return;
    setRegenerating(true);
    setRegenError(null);
    try {
      const updated = await api.regenerateAsset(conn, current.id, feedback.trim());
      setCurrent(updated);
      setHtml(assetToOutlookHtml(updated.headline, updated.body, updated.call_to_action));
      setPlain(plainOf(updated));
      setDirty(false);
      setFeedback("");
      setFeedbackOpen(false);
      onSaved?.();
    } catch (err) {
      setRegenError(err instanceof Error ? err.message : String(err));
    } finally {
      setRegenerating(false);
    }
  }

  function requestClose() {
    if (dirty && !window.confirm("You have unsaved changes to this content. Discard them?")) return;
    onClose();
  }

  function exec(cmd: string) {
    document.execCommand(cmd);
    setDirty(true);
    richRef.current?.focus();
  }

  function downloadHtml() {
    downloadFile(`${asset.id}.html`, `<!doctype html><html><body>${html}</body></html>`, "text/html");
  }
  function downloadRich() {
    const source = richRef.current?.innerText ?? plain;
    downloadFile(`${asset.id}.rtf`, toRtf(source), "application/rtf");
  }
  function downloadPlain() {
    downloadFile(`${asset.id}.txt`, plain, "text/plain");
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const source =
        tab === "plain" ? plain : tab === "rich" ? richRef.current?.innerText ?? plain : stripHtml(html);
      const patch = splitParts(source);
      if (Object.keys(patch).length) {
        const updated = await api.updateAsset(conn, current.id, patch);
        setCurrent(updated);
      }
      setDirty(false);
      onSaved?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  const subtitle = (
    <span className="row gap-sm" style={{ display: "inline-flex", alignItems: "center" }}>
      <ChannelIcon channel={current.channel} size={13} /> {current.channel}
    </span>
  );

  return (
    <Drawer title={current.headline || "Untitled content"} subtitle={subtitle} onClose={requestClose}>
      {error && <div className="banner danger" style={{ marginBottom: 14 }}><span>✕</span><div>{error}</div></div>}

      <div className="regen-box">
        <button
          type="button"
          className="regen-toggle"
          onClick={() => setFeedbackOpen((o) => !o)}
        >
          <span>✎ Not happy with this? Tell us what's wrong</span>
          <span className="dim">{feedbackOpen ? "▲" : "▼"}</span>
        </button>
        {!!current.feedback_history?.length && (
          <div className="col gap-sm" style={{ marginTop: 10 }}>
            <div className="dim" style={{ fontSize: 11.5 }}>
              Earlier feedback still being applied:{" "}
              {current.feedback_history.slice(-4).map((h, i) => (
                <span key={i}>{i > 0 && " · "}“{h.feedback}”</span>
              ))}
            </div>
            {current.qa_passed === true && (
              <div style={{ fontSize: 12, color: "var(--ok)" }}>
                ✓ Checked against your brand rules: passed
                {current.qa_auto_fixed ? " (one issue was found and fixed automatically)" : ""}.
              </div>
            )}
            {current.qa_passed === false && (
              <div className="banner warn" style={{ margin: 0 }}>
                <span>⚠</span>
                <div>
                  <strong>Still flagged after one automatic fix.</strong> Review before using:
                  <ul className="list-tight" style={{ margin: "4px 0 0" }}>
                    {(current.qa_issues ?? []).filter((q) => q.severity === "critical").map((q, i) => (
                      <li key={i}>{q.issue}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
            {current.qa_passed == null && (
              <div className="dim" style={{ fontSize: 12 }}>The brand-rule check couldn't run on this version.</div>
            )}
          </div>
        )}
        {feedbackOpen && (
          <div className="col gap-sm" style={{ marginTop: 10 }}>
            <textarea
              className="textarea"
              style={{ minHeight: 70 }}
              placeholder="e.g. too formal, missing the discount code, CTA should link to the pricing page…"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              disabled={regenerating}
            />
            {regenError && (
              <div className="banner danger" style={{ margin: 0 }}><span>✕</span><div>{regenError}</div></div>
            )}
            <div className="row">
              <button className="btn primary sm" onClick={regenerate} disabled={regenerating || !feedback.trim()}>
                {regenerating ? "Regenerating…" : "↻ Regenerate with this feedback"}
              </button>
              <span className="dim" style={{ fontSize: 11 }}>
                Reuses this campaign's research &amp; strategy, then checks the result against your brand rules.
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="row" style={{ marginBottom: 14 }}>
        <div className="tabs">
          {availableTabs.map((t) => (
            <button key={t} className={"tab" + (tab === t ? " active" : "")} onClick={() => setTab(t)}>
              {TAB_LABEL[t]}
            </button>
          ))}
        </div>
        <span className="spacer" />
        {dirty && <span className="dim" style={{ fontSize: 11.5 }}>Unsaved changes</span>}
      </div>

      {tab === "html" && (
        <div className="col gap-sm">
          <p className="dim" style={{ fontSize: 11.5, margin: 0 }}>
            Inline-styled, table-based markup — built for Outlook's rendering engine, not a browser.
          </p>
          <textarea
            className="textarea mono"
            style={{ minHeight: 320 }}
            value={html}
            onChange={(e) => { setHtml(e.target.value); setDirty(true); }}
          />
          <div className="row">
            <button className="btn ghost sm" onClick={downloadHtml}>Download .html</button>
          </div>
        </div>
      )}

      {tab === "rich" && (
        <div className="col gap-sm">
          <div className="row gap-sm">
            <button className="btn ghost sm" onClick={() => exec("bold")}><b>B</b></button>
            <button className="btn ghost sm" onClick={() => exec("italic")}><i>I</i></button>
            <button className="btn ghost sm" onClick={() => exec("underline")}><u>U</u></button>
            <button className="btn ghost sm" onClick={() => exec("insertUnorderedList")}>• List</button>
          </div>
          <div
            ref={richRef}
            className="rich-editor"
            contentEditable
            suppressContentEditableWarning
            onInput={() => setDirty(true)}
            dangerouslySetInnerHTML={{ __html: html }}
          />
          <div className="row">
            <button className="btn ghost sm" onClick={downloadRich}>Download .rtf</button>
          </div>
        </div>
      )}

      {tab === "plain" && (
        <div className="col gap-sm">
          <textarea
            className="textarea"
            style={{ minHeight: 320 }}
            value={plain}
            onChange={(e) => { setPlain(e.target.value); setDirty(true); }}
          />
          <div className="row">
            <button className="btn ghost sm" onClick={downloadPlain}>Download .txt</button>
            <button
              className="btn ghost sm"
              onClick={() => { setPlain(stripHtml(richRef.current?.innerHTML ?? html)); setDirty(true); }}
              title="Replace with a text-only version of the Rich Text tab"
            >
              Pull from Rich Text
            </button>
          </div>
        </div>
      )}

      <div className="row" style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--border-soft)" }}>
        <button className="btn primary" onClick={save} disabled={saving || !dirty}>
          {saving ? "Saving…" : "Save"}
        </button>
        <button className="btn ghost" onClick={onClose}>
          {dirty ? "Discard & close" : "Close"}
        </button>
      </div>
    </Drawer>
  );
}
