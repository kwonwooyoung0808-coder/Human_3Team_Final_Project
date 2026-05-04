import { apiGet } from './client'
import type { AuditLogResponse } from '../types/audit'

export function getAuditLogs(limit: number) {
  return apiGet<AuditLogResponse[]>(`/api/v1/audit-logs?limit=${limit}`)
}
