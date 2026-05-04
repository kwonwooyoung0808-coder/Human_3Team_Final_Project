export type AuditLogResponse = {
  id: number
  run_id: string
  event_type: string
  entity_type: string
  entity_id: string | null
  reason: string
  context: Record<string, unknown>
  created_at: string
}
