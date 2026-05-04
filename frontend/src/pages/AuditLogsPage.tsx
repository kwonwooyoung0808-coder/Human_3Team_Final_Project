import { useEffect, useState } from 'react'

import DataTable from '../components/DataTable'
import ErrorBanner from '../components/ErrorBanner'
import JsonBlock from '../components/JsonBlock'
import { getAuditLogs } from '../api/audit'
import { useApi } from '../hooks/useApi'

export default function AuditLogsPage() {
  const [limit, setLimit] = useState(10)
  const { data, loading, error, execute } = useApi(getAuditLogs)

  useEffect(() => {
    void execute(limit)
  }, [execute, limit])

  return (
    <section className="page">
      <div className="section-head">
        <div>
          <p className="eyebrow">GET /api/v1/audit-logs</p>
          <h2>Audit Logs</h2>
        </div>
      </div>

      <div className="card inline-form">
        <label>
          <span>Limit</span>
          <input
            type="number"
            min={1}
            max={100}
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
          />
        </label>
        <button onClick={() => void execute(limit)} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      <ErrorBanner message={error} />

      {data ? (
        <section className="card">
          <DataTable
            rows={data}
            columns={[
              { key: 'run_id', header: 'Run ID', render: (row) => row.run_id },
              { key: 'event_type', header: 'Event', render: (row) => row.event_type },
              { key: 'entity_type', header: 'Entity Type', render: (row) => row.entity_type },
              { key: 'reason', header: 'Reason', render: (row) => row.reason },
              { key: 'created_at', header: 'Created At', render: (row) => row.created_at },
            ]}
          />

          <div>
            <span className="label">Latest Payload</span>
            <JsonBlock value={data[0] ?? []} />
          </div>
        </section>
      ) : null}
    </section>
  )
}
