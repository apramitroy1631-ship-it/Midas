import { useState } from "react";
import { Badge, Card, Drawer, Empty, Field, SectionHead } from "../components/ui";
import { api } from "../lib/api";
import type { Brand, Connection } from "../lib/types";

const BLANK = {
  name: "",
  description: "",
  industry: "",
  tone: "",
  usp: "",
  target_audience: "",
  website: "",
  visual_style: "",
  preferred_channels: "",
  content_restrictions: "",
};

type Form = typeof BLANK;

function toForm(b: Brand): Form {
  const g = b.memory?.brand_guidelines ?? {};
  return {
    name: b.name,
    description: b.description,
    industry: b.industry,
    tone: b.tone,
    usp: b.usp,
    target_audience: b.target_audience,
    website: b.website,
    visual_style: g.visual_style ?? "",
    preferred_channels: (g.preferred_channels ?? []).join(", "),
    content_restrictions: (g.content_restrictions ?? []).join("\n"),
  };
}

function toPayload(f: Form) {
  return {
    name: f.name,
    description: f.description,
    industry: f.industry,
    tone: f.tone,
    usp: f.usp,
    target_audience: f.target_audience,
    website: f.website,
    brand_guidelines: {
      visual_style: f.visual_style,
      preferred_channels: f.preferred_channels.split(",").map((s) => s.trim()).filter(Boolean),
      content_restrictions: f.content_restrictions.split("\n").map((s) => s.trim()).filter(Boolean),
    },
  };
}

export function Brands({
  conn,
  brands,
  onChanged,
}: {
  conn: Connection;
  brands: Brand[];
  onChanged: () => void;
}) {
  const [editing, setEditing] = useState<Brand | "new" | null>(null);
  const [form, setForm] = useState<Form>(BLANK);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function open(target: Brand | "new") {
    setEditing(target);
    setForm(target === "new" ? BLANK : toForm(target));
    setError(null);
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      if (editing === "new") await api.createBrand(conn, toPayload(form));
      else if (editing) await api.updateBrand(conn, editing.id, toPayload(form));
      setEditing(null);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  async function remove(brand: Brand) {
    if (!confirm(`Delete "${brand.name}"? Its runs and assets stay, but nothing new can be generated for it.`)) return;
    await api.deleteBrand(conn, brand.id);
    setEditing(null);
    onChanged();
  }

  const set = (k: keyof Form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <>
      <SectionHead action={<button className="btn primary sm" onClick={() => open("new")}>Add brand</button>}>
        Brands
      </SectionHead>

      {brands.length === 0 ? (
        <Card>
          <Empty
            icon="◇"
            title="No brands yet"
            text="A brand is what binds the agents: its voice, its USP, and above all its content restrictions, which QA treats as absolute."
            action={<button className="btn primary sm" onClick={() => open("new")} style={{ marginTop: 8 }}>Add the first brand</button>}
          />
        </Card>
      ) : (
        <div className="grid grid-2">
          {brands.map((b) => {
            const memory = b.memory ?? {};
            const restrictions = memory.brand_guidelines?.content_restrictions ?? [];
            return (
              <Card key={b.id} title={b.name} sub={b.industry} action={
                <button className="btn ghost sm" onClick={() => open(b)}>Edit</button>
              }>
                <p className="muted" style={{ fontSize: 12.5, marginTop: 0, lineHeight: 1.6 }}>{b.description}</p>
                <dl className="kv" style={{ fontSize: 12.5, marginTop: 12 }}>
                  <dt>USP</dt><dd>{b.usp || "—"}</dd>
                  <dt>Tone</dt><dd className="muted">{b.tone || "—"}</dd>
                  <dt>Restrictions</dt><dd className="mono">{restrictions.length}</dd>
                </dl>
                <div className="row wrap" style={{ marginTop: 12 }}>
                  <Badge tone="muted">{(memory.latest_insights ?? []).length} insights</Badge>
                  <Badge tone="ok">{(memory.winning_angles ?? []).length} winning</Badge>
                  <Badge tone="warn">{(memory.exhausted_angles ?? []).length} exhausted</Badge>
                  <Badge tone="info">{(memory.past_campaigns ?? []).length} campaigns</Badge>
                </div>
                {!!(memory.latest_insights ?? []).length && (
                  <div style={{ marginTop: 14 }}>
                    <div className="field-label">Learned by the system</div>
                    <ul className="list-tight muted" style={{ fontSize: 12.5 }}>
                      {(memory.latest_insights ?? []).slice(-3).map((x, i) => (
                        <li key={i}>{x}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}

      {editing && (
        <Drawer
          title={editing === "new" ? "New brand" : "Edit brand"}
          subtitle="What the agents are bound by on every run"
          onClose={() => setEditing(null)}
        >
          {error && <div className="banner danger"><span>✕</span><div>{error}</div></div>}

          <Field label="Name"><input className="input" value={form.name} onChange={set("name")} /></Field>
          <Field label="Description"><textarea className="textarea" value={form.description} onChange={set("description")} /></Field>
          <Field label="Industry"><input className="input" value={form.industry} onChange={set("industry")} /></Field>
          <Field label="Tone" hint="Written as direction to a copywriter, not as adjectives.">
            <input className="input" value={form.tone} onChange={set("tone")} />
          </Field>
          <Field label="USP" hint="The one specific thing this brand can claim that competitors can't.">
            <input className="input" value={form.usp} onChange={set("usp")} />
          </Field>
          <Field label="Default target audience"><input className="input" value={form.target_audience} onChange={set("target_audience")} /></Field>
          <Field label="Website"><input className="input mono" value={form.website} onChange={set("website")} /></Field>

          <div className="section-head"><h2>Guidelines</h2><span className="rule" /></div>

          <Field label="Visual style"><input className="input" value={form.visual_style} onChange={set("visual_style")} /></Field>
          <Field label="Preferred channels" hint="Comma separated. The Director may still deviate with a reason.">
            <input className="input mono" value={form.preferred_channels} onChange={set("preferred_channels")} />
          </Field>
          <Field
            label="Content restrictions"
            hint="One per line. These are absolute — QA treats a breach as a blocking failure, which is what forces a revision cycle."
          >
            <textarea className="textarea" style={{ minHeight: 110 }} value={form.content_restrictions} onChange={set("content_restrictions")} />
          </Field>

          <div className="row" style={{ marginTop: 18 }}>
            <button className="btn primary" onClick={save} disabled={saving || !form.name}>
              {saving ? "Saving…" : "Save brand"}
            </button>
            <button className="btn ghost" onClick={() => setEditing(null)}>Cancel</button>
            <span className="spacer" />
            {editing !== "new" && (
              <button className="btn danger ghost" onClick={() => remove(editing)}>Delete</button>
            )}
          </div>
        </Drawer>
      )}
    </>
  );
}
