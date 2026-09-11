import { useState, useEffect } from 'react'
import { api } from '../api'

export default function DashboardTab() {
  const [health, setHealth] = useState<{ status: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.health()
      .then(setHealth)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <h1 className="tab-title">Dashboard</h1>
      <div className="card" style={{ maxWidth: 420 }}>
        <div className="tab-section">
          <div className="tab-section-title">API Health</div>
          {loading && <p style={{ color: 'var(--text-muted)' }}>Checking…</p>}
          {error && (
            <div className="message error">
              Backend unreachable: {error}. Start the FastAPI server (e.g. on port 8000) and ensure the dev proxy is used.
            </div>
          )}
          {health && !error && (
            <div className="message success">
              Status: <strong>{health.status}</strong>
            </div>
          )}
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.75rem' }}>
          Use the <strong>Brands</strong> tab to create and manage brands, and the <strong>Campaigns</strong> tab to create campaigns.
        </p>
      </div>
    </>
  )
}
