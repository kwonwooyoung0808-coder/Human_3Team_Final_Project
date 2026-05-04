import { useState } from 'react'

import ErrorBanner from '../components/ErrorBanner'
import JsonBlock from '../components/JsonBlock'
import StatusBadge from '../components/StatusBadge'
import { getRun } from '../api/runs'
import { useApi } from '../hooks/useApi'

export default function RunPage() {
  const [runId, setRunId] = useState('run_web_demo_001')
  const { data, loading, error, execute } = useApi(getRun)

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await execute(runId)
  }

  return (
    <section className="page">
      <div className="section-head">
        <div>
          <p className="eyebrow">GET /api/v1/runs/{'{run_id}'}</p>
          <h2>Run Lookup</h2>
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
        <section className="card result-card">
          <div className="result-grid">
            <article>
              <span className="label">Final Status</span>
              <StatusBadge value={data.final_status} />
            </article>
            <article>
              <span className="label">Final Action</span>
              <StatusBadge value={data.final_action} />
            </article>
            <article>
              <span className="label">Has Violation</span>
              <StatusBadge value={data.has_violation} />
            </article>
          </div>

          <div>
            <span className="label">Input</span>
            <JsonBlock value={data.input} />
          </div>
          <div>
            <span className="label">Output</span>
            <JsonBlock value={data.output} />
          </div>
          <div>
            <span className="label">Context</span>
            <JsonBlock value={data.context} />
          </div>
        </section>
      ) : null}
    </section>
  )
}
