import type { PropsWithChildren } from 'react'
import { Link } from 'react-router-dom'

import NavTabs from './NavTabs'

export default function Layout({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Governance Console</p>
          <h1>SafeAgent_Manager</h1>
        </div>
        <div className="header-links">
          <Link to="/">Evaluate</Link>
          <a href="/docs" target="_blank" rel="noreferrer">
            Swagger
          </a>
        </div>
      </header>

      <NavTabs />

      <main className="page-container">{children}</main>
    </div>
  )
}
