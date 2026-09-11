import { useMemo, useState } from "react";
import { Badge, Card, Chips, Empty, timeAgo } from "../components/ui";
import type { Asset, Brand } from "../lib/types";

export function Library({ assets, brands }: { assets: Asset[]; brands: Brand[] }) {
  const [brandId, setBrandId] = useState("");
  const [channel, setChannel] = useState("");
  const [copied, setCopied] = useState<string | null>(null);

  const channels = useMemo(
    () => Array.from(new Set(assets.map((a) => a.channel))).sort(),
    [assets]
  );

  const filtered = assets.filter(
    (a) => (!brandId || a.brand_id === brandId) && (!channel || a.channel === channel)
  );

  async function copy(asset: Asset) {
    const text = `${asset.headline}\n\n${asset.body}\n\n${asset.call_to_action}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(asset.id);
      setTimeout(() => setCopied(null), 1600);
    } catch {
      /* clipboard blocked — the copy simply doesn't happen */
    }
  }

  if (!assets.length) {
    return (
      <Empty
        icon="▤"
        title="The library is empty"
        text="Assets land here automatically the moment QA passes a run. Nothing needs approving first."
      />
    );
  }

  return (
    <div className="col">
      <Card>
        <div className="row wrap">
          <select className="select" style={{ width: 200 }} value={brandId} onChange={(e) => setBrandId(e.target.value)}>
            <option value="">All brands</option>
            {brands.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
          <select className="select" style={{ width: 160 }} value={channel} onChange={(e) => setChannel(e.target.value)}>
            <option value="">All channels</option>
            {channels.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <span className="spacer" />
          <span className="mono dim">{filtered.length} assets</span>
        </div>
      </Card>

      <div className="grid grid-2">
        {filtered.map((a) => (
          <div className="asset" key={a.id}>
            <div className="asset-head">
              <Badge tone="info">{a.channel}</Badge>
              <Badge tone={a.status === "published" ? "ok" : "warn"}>{a.status.replace("_", " ")}</Badge>
              <span className="spacer" />
              <span className="dim" style={{ fontSize: 11.5 }}>{timeAgo(a.created_at)}</span>
            </div>

            <div className="asset-headline">{a.headline}</div>
            <div className="asset-body">{a.body}</div>
            <div className="asset-cta">→ {a.call_to_action}</div>

            {a.seo && (
              <div className="asset-seo">
                <Chips items={[a.seo.primary_keyword, ...(a.seo.hashtags ?? [])]} />
              </div>
            )}

            <div className="row" style={{ marginTop: 4 }}>
              <span className="dim" style={{ fontSize: 11.5 }}>{a.brand_name}</span>
              <span className="spacer" />
              <button className="btn ghost sm" onClick={() => copy(a)}>
                {copied === a.id ? "Copied" : "Copy"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
