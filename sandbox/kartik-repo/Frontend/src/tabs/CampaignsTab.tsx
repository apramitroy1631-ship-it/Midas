import { useState, useEffect, useCallback } from 'react'
import { api, BrandSummary, Campaign, CampaignCreateResponse } from '../api'

type Toast = { id: number; type: 'success' | 'error'; text: string }

function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([])
  const add = useCallback((type: 'success' | 'error', text: string) => {
    const id = Date.now()
    setToasts((t) => [...t, { id, type, text }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5000)
  }, [])
  return { toasts, addToast: add }
}

export default function CampaignsTab() {
  const { toasts, addToast } = useToast()
  const [brands, setBrands] = useState<BrandSummary[]>([])
  const [brandsLoading, setBrandsLoading] = useState(true)
  const [selectedBrandId, setSelectedBrandId] = useState<string>('')
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [campaignsLoading, setCampaignsLoading] = useState(false)
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [createForm, setCreateForm] = useState({ goal: '', target_audience: '', budget: '' })
  const [createLoading, setCreateLoading] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  useEffect(() => {
    api.brands
      .list()
      .then(setBrands)
      .catch(() => addToast('error', 'Failed to load brands'))
      .finally(() => setBrandsLoading(false))
  }, [addToast])

  const loadCampaigns = useCallback(
    (brandId: string) => {
      if (!brandId) {
        setCampaigns([])
        return
      }
      setCampaignsLoading(true)
      setCampaigns([])
      setSelectedCampaign(null)
      setExpandedId(null)
      api.campaigns
        .list(brandId)
        .then(setCampaigns)
        .catch(() => addToast('error', 'Failed to load campaigns'))
        .finally(() => setCampaignsLoading(false))
    },
    [addToast]
  )

  useEffect(() => {
    if (selectedBrandId) loadCampaigns(selectedBrandId)
    else setCampaigns([])
  }, [selectedBrandId, loadCampaigns])

  const loadCampaignDetail = async (brandId: string, campaignId: string) => {
    setDetailLoading(true)
    setSelectedCampaign(null)
    try {
      const c = await api.campaigns.get(brandId, campaignId)
      setSelectedCampaign(c)
      setExpandedId(campaignId)
    } catch {
      addToast('error', 'Failed to load campaign details')
    } finally {
      setDetailLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedBrandId) {
      addToast('error', 'Select a brand first')
      return
    }
    const budget = parseFloat(createForm.budget)
    if (isNaN(budget) || budget < 0) {
      addToast('error', 'Budget must be a positive number')
      return
    }
    setCreateLoading(true)
    try {
      const res: CampaignCreateResponse = await api.campaigns.create(selectedBrandId, {
        goal: createForm.goal,
        target_audience: createForm.target_audience,
        budget,
      })
      addToast('success', `Campaign created: ${res.id} (${res.status})`)
      setCreateForm({ goal: '', target_audience: '', budget: '' })
      loadCampaigns(selectedBrandId)
    } catch (err) {
      addToast('error', err instanceof Error ? err.message : 'Create campaign failed')
    } finally {
      setCreateLoading(false)
    }
  }

  const handleDelete = async (brandId: string, campaignId: string) => {
    setDeleteLoading(campaignId)
    setDeleteConfirm(null)
    try {
      await api.campaigns.delete(brandId, campaignId)
      addToast('success', 'Campaign deleted')
      if (selectedCampaign?.id === campaignId) setSelectedCampaign(null)
      setExpandedId(null)
      loadCampaigns(brandId)
    } catch {
      addToast('error', 'Failed to delete campaign')
    } finally {
      setDeleteLoading(null)
    }
  }

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)

  return (
    <>
      <h1 className="tab-title">Campaigns</h1>

      <div className="toast-stack">
        {toasts.map((t) => (
          <div key={t.id} className={`message ${t.type} toast-msg`}>
            {t.text}
          </div>
        ))}
      </div>

      <div className="campaigns-layout">
        <section className="card campaigns-sidebar">
          <h2 className="campaigns-section-head">Brand</h2>
          {brandsLoading ? (
            <p className="campaigns-muted">Loading brands…</p>
          ) : brands.length === 0 ? (
            <p className="campaigns-muted">No brands. Create one in the Brands tab.</p>
          ) : (
            <div className="campaigns-brand-list">
              {brands.map((b) => (
                <button
                  key={b.id}
                  type="button"
                  className={`campaigns-brand-btn ${selectedBrandId === b.id ? 'active' : ''}`}
                  onClick={() => setSelectedBrandId(b.id)}
                >
                  <span className="campaigns-brand-name">{b.name || '(Unnamed)'}</span>
                  <span className="campaigns-brand-id">{b.id}</span>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="card campaigns-main">
          {!selectedBrandId ? (
            <div className="campaigns-empty-state">
              <div className="campaigns-empty-icon">📋</div>
              <p>Select a brand to view and manage campaigns</p>
            </div>
          ) : (
            <>
              <div className="campaigns-main-header">
                <h2 className="campaigns-section-head">Campaigns</h2>
                <button
                  type="button"
                  className="btn btn-ghost campaigns-refresh"
                  onClick={() => loadCampaigns(selectedBrandId)}
                  disabled={campaignsLoading}
                >
                  {campaignsLoading ? 'Loading…' : 'Refresh'}
                </button>
              </div>

              {campaignsLoading ? (
                <div className="campaigns-skeleton">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="campaigns-skeleton-card" />
                  ))}
                </div>
              ) : campaigns.length === 0 ? (
                <div className="campaigns-empty-state campaigns-empty-inline">
                  <p>No campaigns yet. Create one below.</p>
                </div>
              ) : (
                <ul className="campaigns-list">
                  {campaigns.map((c) => (
                    <li key={c.id} className="campaigns-list-item">
                      <div
                        className="campaign-card"
                        role="button"
                        tabIndex={0}
                        onClick={() => loadCampaignDetail(selectedBrandId, c.id)}
                        onKeyDown={(e) => e.key === 'Enter' && loadCampaignDetail(selectedBrandId, c.id)}
                      >
                        <div className="campaign-card-top">
                          <span className={`campaign-status campaign-status-${c.status}`}>{c.status}</span>
                          <span className="campaign-goal">{c.goal || '—'}</span>
                        </div>
                        <div className="campaign-card-meta">
                          <span>{c.target_audience || '—'}</span>
                          <span>{formatCurrency(Number(c.budget))}</span>
                        </div>
                        <div className="campaign-card-id">{c.id}</div>
                      </div>

                      {expandedId === c.id && (
                        <div className="campaign-detail">
                          {detailLoading ? (
                            <p className="campaigns-muted">Loading…</p>
                          ) : selectedCampaign && selectedCampaign.id === c.id ? (
                            <>
                              <div className="campaign-detail-grid">
                                <div className="campaign-detail-field">
                                  <span className="campaign-detail-label">Goal</span>
                                  <span>{selectedCampaign.goal || '—'}</span>
                                </div>
                                <div className="campaign-detail-field">
                                  <span className="campaign-detail-label">Target audience</span>
                                  <span>{selectedCampaign.target_audience || '—'}</span>
                                </div>
                                <div className="campaign-detail-field">
                                  <span className="campaign-detail-label">Budget</span>
                                  <span>{formatCurrency(Number(selectedCampaign.budget))}</span>
                                </div>
                                {selectedCampaign.created_at && (
                                  <div className="campaign-detail-field">
                                    <span className="campaign-detail-label">Created</span>
                                    <span>{new Date(selectedCampaign.created_at).toLocaleString()}</span>
                                  </div>
                                )}
                              </div>
                              {(selectedCampaign.research ?? selectedCampaign.strategy ?? selectedCampaign.content) && (
                                <details className="campaign-detail-raw">
                                  <summary>Raw data</summary>
                                  <pre>{JSON.stringify(
                                    {
                                      research: selectedCampaign.research,
                                      strategy: selectedCampaign.strategy,
                                      content: selectedCampaign.content,
                                      qa_report: selectedCampaign.qa_report,
                                      analytics: selectedCampaign.analytics,
                                    },
                                    null,
                                    2
                                  )}</pre>
                                </details>
                              )}
                              <div className="campaign-detail-actions">
                                <button
                                  type="button"
                                  className="btn btn-ghost btn-sm"
                                  onClick={() => setExpandedId(null)}
                                >
                                  Close
                                </button>
                                {deleteConfirm === c.id ? (
                                  <>
                                    <span className="campaign-delete-confirm">Delete this campaign?</span>
                                    <button
                                      type="button"
                                      className="btn btn-danger btn-sm"
                                      onClick={() => handleDelete(selectedBrandId, c.id)}
                                      disabled={deleteLoading === c.id}
                                    >
                                      {deleteLoading === c.id ? 'Deleting…' : 'Yes, delete'}
                                    </button>
                                    <button
                                      type="button"
                                      className="btn btn-ghost btn-sm"
                                      onClick={() => setDeleteConfirm(null)}
                                    >
                                      Cancel
                                    </button>
                                  </>
                                ) : (
                                  <button
                                    type="button"
                                    className="btn btn-danger btn-sm"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      setDeleteConfirm(c.id)
                                    }}
                                  >
                                    Delete
                                  </button>
                                )}
                              </div>
                            </>
                          ) : null}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}

              <div className="card campaigns-create-section">
                <h2 className="campaigns-section-head">Create campaign</h2>
                <form onSubmit={handleCreate} className="campaigns-create-form">
                  <div className="form-grid">
                    <div className="form-group full">
                      <label className="label">Goal</label>
                      <input
                        value={createForm.goal}
                        onChange={(e) => setCreateForm((f) => ({ ...f, goal: e.target.value }))}
                        placeholder="e.g. Increase sign-ups by 20%"
                        required
                      />
                    </div>
                    <div className="form-group full">
                      <label className="label">Target audience</label>
                      <input
                        value={createForm.target_audience}
                        onChange={(e) => setCreateForm((f) => ({ ...f, target_audience: e.target.value }))}
                        placeholder="e.g. B2B decision makers, 25–44"
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label className="label">Budget (USD)</label>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={createForm.budget}
                        onChange={(e) => setCreateForm((f) => ({ ...f, budget: e.target.value }))}
                        placeholder="0.00"
                        required
                      />
                    </div>
                  </div>
                  <div className="form-actions">
                    <button type="submit" className="btn btn-primary" disabled={createLoading}>
                      {createLoading ? 'Creating…' : 'Create campaign'}
                    </button>
                  </div>
                </form>
              </div>
            </>
          )}
        </section>
      </div>
    </>
  )
}
