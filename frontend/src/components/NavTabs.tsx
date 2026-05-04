import { NavLink } from 'react-router-dom'

const tabs = [
  { to: '/', label: 'Evaluate' },
  { to: '/runs', label: 'Run Lookup' },
  { to: '/trace', label: 'Trace' },
  { to: '/violations', label: 'Violations' },
  { to: '/audit-logs', label: 'Audit Logs' },
]

export default function NavTabs() {
  return (
    <nav className="tabs">
      {tabs.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.to === '/'}
          className={({ isActive }) => (isActive ? 'tab active' : 'tab')}
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  )
}
