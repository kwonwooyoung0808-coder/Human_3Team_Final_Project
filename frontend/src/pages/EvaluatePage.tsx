import { useState } from 'react'

import { evaluatePolicy } from '../api/evaluate'
import ErrorBanner from '../components/ErrorBanner'
import JsonBlock from '../components/JsonBlock'
import StatusBadge from '../components/StatusBadge'
import { useApi } from '../hooks/useApi'

const defaultContext = `{
  "workflow_name": "governance_workflow",
  "user_id": "demo_user"
}`

const defaultRetrievedContext = `[
  "이 시스템은 2026년에 출시되었습니다."
]`

const defaultResponse = `{
  "summary": "이 시스템은 2026년에 출시되었습니다.",
  "evidence": "retrieved_context에 동일 문장이 있습니다.",
  "disclaimer": "추가 검토가 필요할 수 있습니다."
}`

export default function EvaluatePage() {
  const [runId, setRunId] = useState('run_web_pass_001')
  const [input, setInput] = useState('제품 출시 시점을 요약해줘.')
  const [response, setResponse] = useState(defaultResponse)
  const [contextText, setContextText] = useState(defaultContext)
  const [retrievedContextText, setRetrievedContextText] = useState(defaultRetrievedContext)
  const { data, loading, error, execute } = useApi(evaluatePolicy)

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const payload = {
      run_id: runId,
      input,
      response,
      context: JSON.parse(contextText) as Record<string, unknown>,
      retrieved_context: JSON.parse(retrievedContextText) as string[],
    }

    await execute(payload)
  }

  return (
    <section className="page">
      <div className="section-head">
        <div>
          <p className="eyebrow">POST /api/v1/evaluate</p>
          <h2>Policy Evaluation</h2>
        </div>
      </div>

      <form className="card form-grid" onSubmit={onSubmit}>
        <label>
          <span>Run ID</span>
          <input value={runId} onChange={(event) => setRunId(event.target.value)} />
        </label>

        <label className="full">
          <span>Input</span>
          <textarea rows={4} value={input} onChange={(event) => setInput(event.target.value)} />
        </label>

        <label className="full">
          <span>Response</span>
          <textarea rows={5} value={response} onChange={(event) => setResponse(event.target.value)} />
        </label>

        <label className="full">
          <span>Context (JSON)</span>
          <textarea
            rows={6}
            value={contextText}
            onChange={(event) => setContextText(event.target.value)}
          />
        </label>

        <label className="full">
          <span>Retrieved Context (JSON array)</span>
          <textarea
            rows={6}
            value={retrievedContextText}
            onChange={(event) => setRetrievedContextText(event.target.value)}
          />
        </label>

        <div className="actions full">
          <button type="submit" disabled={loading}>
            {loading ? 'Evaluating...' : 'Execute'}
          </button>
        </div>
      </form>

      <ErrorBanner message={error} />

      {data ? (
        <section className="card result-card">
          <div className="result-grid">
            <article>
              <span className="label">Run ID</span>
              <strong>{data.run_id}</strong>
            </article>
            <article>
              <span className="label">Has Violation</span>
              <StatusBadge value={data.has_violation} />
            </article>
            <article>
              <span className="label">Final Action</span>
              <StatusBadge value={data.final_action} />
            </article>
          </div>

          <div>
            <span className="label">Final Response</span>
            <JsonBlock value={data.final_response} />
          </div>

          <div>
            <span className="label">Violations</span>
            <JsonBlock value={data.violations} />
          </div>
        </section>
      ) : null}
    </section>
  )
}
