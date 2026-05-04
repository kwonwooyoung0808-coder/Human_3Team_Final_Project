import { apiGet } from './client'
import type { Violation } from '../types/workflow'

export function getViolations(limit: number) {
  return apiGet<Violation[]>(`/api/v1/violations?limit=${limit}`)
}
