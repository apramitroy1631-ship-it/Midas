import { useMemo, useState } from "react";
import { AssetEditor } from "../components/AssetEditor";
import { ChannelIcon } from "../components/ChannelIcon";
import { Badge, Card, Chips, Empty, Field, timeAgo } from "../components/ui";
import type { Asset, Brand, Connection } from "../lib/types";

export function Library({
  conn,
  assets,
  brands,
  openAssetId,
  onOpenAsset,
  onCloseAsset,
  onSaved,
}: {
  conn: Connection;
  assets: Asset[];
  brands: Brand[];
  openAssetId?: string | null;
  onOpenAsset?: (id: string) => void;
  onCloseAsset?: () => void;
  onSaved?: () => void;
}) {
  const [brandId, setBrandId] = useState("");
  const [channel, setChannel] = useState("");
  const [search, setSearch] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [copied, setCopied] = useState<string | null>(null);

  const channels = useMemo(
    () => Array.from(new Set(assets.map((a) => a.channel))).sort(),
    [assets]
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const fromTime = from ? new Date(from).getTime() : null;
    const toTime = to ? new Date(to).getTime() + 86_400_000 - 1 : null; // inclusive end of day
    return assets.filter((a) => {
      if (brandId && a.brand_id !== brandId) return false;
      if (channel && a.channel !== channel) return false;
      if (q && !(a.headline + " " + a.body).toLowerCase().includes(q)) return false;
      const created = new Date(a.created_at).getTime();
      if (fromTime && created < fromTime) return false;
      if (toTime && created > toTime) return false;
      return true;
    });
  }, [assets, brandId, channel, search, from, to]);

  const openAsset = openAssetId ? assets.find((a) => a.id === openAssetId) : null;
  const anyFilterActive = !!(brandId || channel || search || from || to);

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
        <div className="row wrap" style={{ marginBottom: 12 }}>
          <input
            className="input"
            style={{ maxWidth: 320 }}
            placeholder="Search headline or body…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select className="select" style={{ width: 180 }} value={brandId} onChange={(e) => setBrandId(e.target.value)}>
            <option value="">All brands</option>
            {brands.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
          <select className="select" style={{ width: 150 }} value={channel} onChange={(e) => setChannel(e.target.value)}>
            <option value="">All channels</option>
            {channels.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className="row wrap">
          <Field label="From">
            <input className="input mono" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </Field>
          <Field label="To">
            <input className="input mono" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </Field>
          <span className="spacer" />
          <div className="row" style={{ alignSelf: "flex-end", marginBottom: 13 }}>
            {anyFilterActive && (
              <button
                className="btn ghost sm"
                onClick={() => { setBrandId(""); setChannel(""); setSearch(""); setFrom(""); setTo(""); }}
              >
                Clear filters
              </button>
            )}
            <span className="mono dim">{filtered.length} / {assets.length} assets</span>
          </div>
        </div>
      </Card>

      {filtered.length === 0 ? (
        <Card>
          <Empty icon="▤" title="Nothing matches" text="Try clearing a filter or broadening the search." />
        </Card>
      ) : (
        <div className="grid grid-2">
          {filtered.map((a) => (
            <div className="asset" key={a.id} onClick={() => onOpenAsset?.(a.id)} style={{ cursor: onOpenAsset ? "pointer" : undefined }}>
              <div className="asset-head">
                <span className="asset-channel-icon"><ChannelIcon channel={a.channel} size={14} /></span>
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
                <button className="btn ghost sm" onClick={(e) => { e.stopPropagation(); copy(a); }}>
                  {copied === a.id ? "Copied" : "Copy"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {openAsset && (
        <AssetEditor asset={openAsset} conn={conn} onClose={() => onCloseAsset?.()} onSaved={onSaved} />
      )}
    </div>
  );
}
