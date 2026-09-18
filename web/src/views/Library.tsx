import { useMemo, useState } from "react";
import { AssetEditor } from "../components/AssetEditor";
import { ChannelIcon } from "../components/ChannelIcon";
import { DateRangePicker } from "../components/DateRangePicker";
import { api } from "../lib/api";
import { Badge, Card, Chips, Empty, timeAgo } from "../components/ui";
import type { Asset, Brand, Connection } from "../lib/types";

const ALL_CHANNELS = ["email", "blog", "linkedin"];

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
  const [channels, setChannels] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [copied, setCopied] = useState<string | null>(null);

  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const knownChannels = useMemo(
    () => Array.from(new Set([...ALL_CHANNELS, ...assets.map((a) => a.channel)])),
    [assets]
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const fromTime = from ? new Date(from).getTime() : null;
    const toTime = to ? new Date(to).getTime() + 86_400_000 - 1 : null; // inclusive end of day
    return assets.filter((a) => {
      if (brandId && a.brand_id !== brandId) return false;
      if (channels.length && !channels.includes(a.channel)) return false;
      if (q && !(a.headline + " " + a.body).toLowerCase().includes(q)) return false;
      const created = new Date(a.created_at).getTime();
      if (fromTime && created < fromTime) return false;
      if (toTime && created > toTime) return false;
      return true;
    });
  }, [assets, brandId, channels, search, from, to]);

  const openAsset = openAssetId ? assets.find((a) => a.id === openAssetId) : null;
  const anyFilterActive = !!(brandId || channels.length || search || from || to);

  function toggleChannel(c: string) {
    setChannels((cs) => (cs.includes(c) ? cs.filter((x) => x !== c) : [...cs, c]));
  }

  function toggleSelected(id: string) {
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function exitSelectMode() {
    setSelectMode(false);
    setSelected(new Set());
  }

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

  async function deleteOne(asset: Asset) {
    if (!confirm(`Delete "${asset.headline || "this content"}"? This removes it from MongoDB permanently.`)) return;
    setDeletingId(asset.id);
    try {
      await api.deleteAsset(conn, asset.id);
      onSaved?.();
    } finally {
      setDeletingId(null);
    }
  }

  async function deleteSelected() {
    const n = selected.size;
    if (!n) return;
    if (!confirm(`Delete ${n} piece${n === 1 ? "" : "s"} of content? This removes them from MongoDB permanently.`)) return;
    setBulkDeleting(true);
    try {
      await api.bulkDeleteAssets(conn, Array.from(selected));
      exitSelectMode();
      onSaved?.();
    } finally {
      setBulkDeleting(false);
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
            style={{ maxWidth: 300 }}
            placeholder="Search headline or body…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select className="select" style={{ width: 170 }} value={brandId} onChange={(e) => setBrandId(e.target.value)}>
            <option value="">All brands</option>
            {brands.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
          <DateRangePicker from={from} to={to} onChange={(f, t) => { setFrom(f); setTo(t); }} />
          <span className="spacer" />
          <button
            className={"btn sm" + (selectMode ? " primary" : " ghost")}
            onClick={() => (selectMode ? exitSelectMode() : setSelectMode(true))}
          >
            {selectMode ? `Cancel (${selected.size} selected)` : "Select"}
          </button>
          {selectMode && (
            <button className="btn danger ghost sm" onClick={deleteSelected} disabled={!selected.size || bulkDeleting}>
              {bulkDeleting ? "Deleting…" : `Delete selected`}
            </button>
          )}
        </div>

        <div className="row wrap">
          <span className="field-label" style={{ margin: 0, alignSelf: "center" }}>Channel</span>
          {knownChannels.map((c) => (
            <button
              key={c}
              type="button"
              className={"chip-toggle" + (channels.includes(c) ? " active" : "")}
              onClick={() => toggleChannel(c)}
            >
              <ChannelIcon channel={c} size={13} /> {c}
            </button>
          ))}
          <span className="spacer" />
          <div className="row" style={{ alignSelf: "center" }}>
            {anyFilterActive && (
              <button
                className="btn ghost sm"
                onClick={() => { setBrandId(""); setChannels([]); setSearch(""); setFrom(""); setTo(""); }}
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
          {filtered.map((a) => {
            const isSelected = selected.has(a.id);
            return (
              <div
                className={"asset" + (isSelected ? " asset-selected" : "")}
                key={a.id}
                onClick={() => (selectMode ? toggleSelected(a.id) : onOpenAsset?.(a.id))}
                style={{ cursor: "pointer" }}
              >
                <div className="asset-head">
                  {selectMode && (
                    <span
                      className={"asset-check" + (isSelected ? " checked" : "")}
                      onClick={(e) => { e.stopPropagation(); toggleSelected(a.id); }}
                    >
                      {isSelected ? "✓" : ""}
                    </span>
                  )}
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
                  {!selectMode && (
                    <button
                      className="btn danger ghost sm"
                      onClick={(e) => { e.stopPropagation(); deleteOne(a); }}
                      disabled={deletingId === a.id}
                      title="Delete this content"
                    >
                      {deletingId === a.id ? "…" : "Delete"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {openAsset && (
        <AssetEditor asset={openAsset} conn={conn} onClose={() => onCloseAsset?.()} onSaved={onSaved} />
      )}
    </div>
  );
}
