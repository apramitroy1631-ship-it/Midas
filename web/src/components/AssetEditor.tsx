import { useRef, useState } from "react";
import { Drawer } from "./ui";
import { assetToOutlookHtml, downloadFile, toRtf } from "../lib/download";
import type { Asset } from "../lib/types";

type Tab = "html" | "rich" | "plain";

function plainOf(a: Asset): string {
  return [a.headline, a.body, a.call_to_action].filter(Boolean).join("\n\n");
}

function stripHtml(html: string): string {
  const div = document.createElement("div");
  div.innerHTML = html;
  return div.innerText;
}

/**
 * A first pass at the "export as HTML / Rich Text / Plain Text for Outlook"
 * goal — raw-source editing rather than a full WYSIWYG engine (that's a
 * much bigger build; see the stored MIDAS email-output-goal memory for the
 * ultimate target). Rich Text here is a real contentEditable surface with
 * basic formatting, downloaded as a plain-text-backed .rtf — Outlook opens
 * it fine, it just won't carry bold/italic through yet.
 */
export function AssetEditor({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const [tab, setTab] = useState<Tab>("html");
  const [html, setHtml] = useState(() => assetToOutlookHtml(asset.headline, asset.body, asset.call_to_action));
  const [plain, setPlain] = useState(() => plainOf(asset));
  const richRef = useRef<HTMLDivElement>(null);

  function exec(cmd: string) {
    document.execCommand(cmd);
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

  return (
    <Drawer title={asset.headline || "Untitled content"} subtitle={asset.channel} onClose={onClose}>
      <div className="row" style={{ marginBottom: 14 }}>
        <div className="tabs">
          <button className={"tab" + (tab === "html" ? " active" : "")} onClick={() => setTab("html")}>HTML</button>
          <button className={"tab" + (tab === "rich" ? " active" : "")} onClick={() => setTab("rich")}>Rich Text</button>
          <button className={"tab" + (tab === "plain" ? " active" : "")} onClick={() => setTab("plain")}>Plain Text</button>
        </div>
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
            onChange={(e) => setHtml(e.target.value)}
          />
          <div className="row">
            <button className="btn primary sm" onClick={downloadHtml}>Download .html</button>
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
            dangerouslySetInnerHTML={{ __html: html }}
          />
          <div className="row">
            <button className="btn primary sm" onClick={downloadRich}>Download .rtf</button>
          </div>
        </div>
      )}

      {tab === "plain" && (
        <div className="col gap-sm">
          <textarea
            className="textarea"
            style={{ minHeight: 320 }}
            value={plain}
            onChange={(e) => setPlain(e.target.value)}
          />
          <div className="row">
            <button className="btn primary sm" onClick={downloadPlain}>Download .txt</button>
            <button
              className="btn ghost sm"
              onClick={() => setPlain(stripHtml(richRef.current?.innerHTML ?? html))}
              title="Replace with a text-only version of the Rich Text tab"
            >
              Pull from Rich Text
            </button>
          </div>
        </div>
      )}
    </Drawer>
  );
}
