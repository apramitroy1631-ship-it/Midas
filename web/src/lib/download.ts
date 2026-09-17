/** Triggers a browser download of in-memory text content — no server round trip. */
export function downloadFile(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Wraps plain text as a minimal, valid RTF document Outlook can open.
 * No rich formatting round-trips through this — see ARCHITECTURE.md if that
 * ever needs to change; for now it's a compatibility-safe plain export.
 */
export function toRtf(plain: string): string {
  const escaped = plain
    .replace(/\\/g, "\\\\")
    .replace(/\{/g, "\\{")
    .replace(/\}/g, "\\}")
    .replace(/\n/g, "\\par\n");
  return `{\\rtf1\\ansi\\ansicpg1252\\deff0\\nouicompat{\\fonttbl{\\f0\\fnil\\fcharset0 Calibri;}}\n\\f0\\fs22 ${escaped}\n}`;
}

/** Outlook's HTML rendering is Word's engine — inline styles + tables, not modern CSS. */
export function assetToOutlookHtml(headline: string, body: string, cta: string): string {
  const bodyHtml = body
    .split(/\n{2,}/)
    .map((p) => `<p style="margin:0 0 14px;">${p.replace(/\n/g, "<br>")}</p>`)
    .join("\n");
  return `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-family:Arial,Helvetica,sans-serif;max-width:600px;">
  <tr><td style="font-size:20px;font-weight:bold;color:#171a21;padding-bottom:14px;">${headline}</td></tr>
  <tr><td style="font-size:14px;line-height:1.6;color:#3a3a3a;">${bodyHtml}</td></tr>
  <tr><td style="padding-top:8px;">
    <a href="#" style="background:#c8283c;color:#ffffff;padding:10px 22px;text-decoration:none;border-radius:4px;display:inline-block;font-size:14px;font-weight:bold;">${cta}</a>
  </td></tr>
</table>`;
}
