import { useState } from 'react'
import BrandsTab from './tabs/BrandsTab'
import CampaignsTab from './tabs/CampaignsTab'
import DashboardTab from './tabs/DashboardTab'
import './App.css'

type TabId = 'dashboard' | 'brands' | 'campaigns'

const TABS: { id: TabId; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'brands', label: 'Brands' },
  { id: 'campaigns', label: 'Campaigns' },
]

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('dashboard')

  return (
    <div className="app">
      <nav className="navbar">
        <div className="nav-brand">
          <span className="nav-logo">M</span>
          <span>Marketing & Growth</span>
        </div>
        <ul className="nav-tabs">
          {TABS.map(({ id, label }) => (
            <li key={id}>
              <button
                className={`nav-tab ${activeTab === id ? 'active' : ''}`}
                onClick={() => setActiveTab(id)}
              >
                {label}
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <main className="main">
        {activeTab === 'dashboard' && <DashboardTab />}
        {activeTab === 'brands' && <BrandsTab />}
        {activeTab === 'campaigns' && <CampaignsTab />}
      </main>
    </div>
  )
}

export default App
