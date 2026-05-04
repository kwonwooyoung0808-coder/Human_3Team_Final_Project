type StatusBadgeProps = {
  value: string | boolean
}

export default function StatusBadge({ value }: StatusBadgeProps) {
  const label = typeof value === 'boolean' ? String(value) : value
  const normalized = label.toLowerCase()
  const className =
    normalized === 'true' || normalized === 'pass' || normalized === 'completed'
      ? 'badge success'
      : normalized === 'false' || normalized === 'block' || normalized === 'flagged'
        ? 'badge danger'
        : 'badge neutral'

  return <span className={className}>{label}</span>
}
