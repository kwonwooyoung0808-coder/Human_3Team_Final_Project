export type EvidenceSpan = {
  text: string
  start_char: number | null
  end_char: number | null
  source: 'rule' | 'judge' | 'fallback'
  condition: string | null
  policy_id: string | null
  confidence: number | null
  human_reason: string | null
}

export type Violation = {
  id: string
  run_id: string
  policy_id: string
  policy_name: string
  reason: string
  source: 'rule' | 'judge'
  recommended_action: 'BLOCK' | 'LOG' | 'FLAGGED'
  risk_score: number
  evidence_span: EvidenceSpan | null
  judge_verdict: string | null
  judge_confidence: number | null
  created_at?: string
}

export type EvaluateRequest = {
  run_id?: string
  input: string
  response?: string
  context: Record<string, unknown>
  retrieved_context?: string[]
}

export type EvaluateResponse = {
  run_id: string
  has_violation: boolean
  final_action: 'BLOCK' | 'LOG' | 'PASS' | 'FLAGGED'
  final_response: string
  violations: Violation[]
}

export type RunResponse = {
  run_id: string
  input: string
  output: string
  final_status: string
  final_action: string
  has_violation: boolean
  workflow_name: string
  context: Record<string, unknown>
  created_at: string
}

export type TraceNodeRead = {
  id: number
  run_id: string
  workflow_name: string
  node_name: string
  node_type: string
  latency_ms: number
  status: string
  created_at: string
}

export type RunTraceSummary = {
  run_id: string
  workflow_name: string
  status: string
  nodes: TraceNodeRead[]
  created_at?: string | null
}
