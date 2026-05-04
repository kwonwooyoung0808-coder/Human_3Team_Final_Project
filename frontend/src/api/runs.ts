import { apiGet } from './client'
import type { RunResponse, RunTraceSummary } from '../types/workflow'

export function getRun(runId: string) {
  return apiGet<RunResponse>(`/api/v1/runs/${encodeURIComponent(runId)}`)
}

export function getTrace(runId: string) {
  return apiGet<RunTraceSummary>(`/api/v1/runs/${encodeURIComponent(runId)}/trace`)
}
