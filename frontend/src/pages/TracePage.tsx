import { useState } from 'react'

import DataTable from '../components/DataTable'
import ErrorBanner from '../components/ErrorBanner'
import StatusBadge from '../components/StatusBadge'
import { getTrace } from '../api/runs'
import { useApi } from '../hooks/useApi'

export default function TracePage() {
  const [runId, setRunId] = useState('run_web_demo_001')
  const { data, loading, error, execute } = useApi(getTrace)

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await execute(runId)
  }

  return (
    <section className="page">
      <div className="section-head">
        <div>
          <p className="eyebrow">GET /api/v1/runs/{'{run_id}'}/trace</p>
          <h2>Execution Trace</h2>
        </div>
      </div>

      <form className="card inline-form" onSubmit={onSubmit}>
        <label>
          <span>Run ID</span>
          <input value={runId} onChange={(event) => setRunId(event.target.value)} />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? 'Loading...' : 'Fetch'}
        </button>
      </form>

      <ErrorBanner message={error} />

      {data ? (
        <section className="card">
          <div className="result-grid">
            <article>
              <span className="label">Workflow</span>
              <strong>{data.workflow_name}</strong>
            </article>
            <article>
              <span className="label">Status</span>
              <StatusBadge value={data.status} />
            </article>
            <article>
              <span className="label">Node Count</span>
              <strong>{data.nodes.length}</strong>
            </article>
          </div>

          <DataTable
            rows={data.nodes}
            columns={[
              { key: 'node_name', header: 'Node', render: (row) => row.node_name },
              { key: 'node_type', header: 'Type', render: (row) => row.node_type },
              { key: 'latency_ms', header: 'Latency (ms)', render: (row) => row.latency_ms },
              { key: 'status', header: 'Status', render: (row) => <StatusBadge value={row.status} /> },
              { key: 'created_at', header: 'Created At', render: (row) => row.created_at },
            ]}
          />
        </section>
      ) : null}
    </section>
  )
}
