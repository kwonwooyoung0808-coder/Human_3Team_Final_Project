import { createBrowserRouter } from 'react-router-dom'

import App from './App'
import AuditLogsPage from './pages/AuditLogsPage'
import EvaluatePage from './pages/EvaluatePage'
import RunPage from './pages/RunPage'
import TracePage from './pages/TracePage'
import ViolationsPage from './pages/ViolationsPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <EvaluatePage /> },
      { path: 'runs', element: <RunPage /> },
      { path: 'trace', element: <TracePage /> },
      { path: 'violations', element: <ViolationsPage /> },
      { path: 'audit-logs', element: <AuditLogsPage /> },
    ],
  },
])
