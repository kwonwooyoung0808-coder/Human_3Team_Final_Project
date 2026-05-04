import { apiPost } from './client'
import type { EvaluateRequest, EvaluateResponse } from '../types/workflow'

export function evaluatePolicy(payload: EvaluateRequest) {
  return apiPost<EvaluateRequest, EvaluateResponse>('/api/v1/evaluate', payload)
}
