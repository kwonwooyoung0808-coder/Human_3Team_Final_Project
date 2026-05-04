import { useEffect, useState } from 'react'

import DataTable from '../components/DataTable'
import ErrorBanner from '../components/ErrorBanner'
import JsonBlock from '../components/JsonBlock'
import StatusBadge from '../components/StatusBadge'
import { getViolations } from '../api/violations'
import { useApi } from '../hooks/useApi'

export default function ViolationsPage() {
  const [limit, setLimit] = useState(10)
  const { data, loading, error, execute } = useApi(getViolations)

  useEffect(() => {
    void execute(limit)
  }, [execute, limit])

  return (
    <section className="page">
      <div className="section-head">
        <div>
          <p className="eyebrow">GET /api/v1/violations</p>
          <h2>Violations</h2>
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
              { key: 'policy_id', header: 'Policy', render: (row) => row.policy_id },
              { key: 'source', header: 'Source', render: (row) => row.source },
              {
                key: 'recommended_action',
                header: 'Action',
                render: (row) => <StatusBadge value={row.recommended_action} />,
              },
              { key: 'risk_score', header: 'Risk Score', render: (row) => row.risk_score },
              { key: 'created_at', header: 'Created At', render: (row) => row.created_at ?? '-' },
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
