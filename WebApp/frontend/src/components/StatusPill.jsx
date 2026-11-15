const TONES_BY_LABEL = {
  analyzed: 'ok',
  complete: 'ok',
  nominal: 'ok',
  low: 'ok',
  'in review': 'accent',
  running: 'accent',
  moderate: 'warning',
  warning: 'warning',
  pending: 'muted',
  queued: 'muted',
  high: 'danger',
}

export default function StatusPill({ children, tone }) {
  const key = String(children).toLowerCase()
  const resolvedTone = tone ?? TONES_BY_LABEL[key] ?? 'muted'

  return (
    <span className={`status-pill status-pill--${resolvedTone}`}>
      {children}
    </span>
  )
}
