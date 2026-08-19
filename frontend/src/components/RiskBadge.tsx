import type { RiskLevel } from '../api/types'

const STYLES: Record<RiskLevel, string> = {
  low: 'bg-status-good/10 text-status-good',
  medium: 'bg-status-warning/15 text-amber-700',
  high: 'bg-status-serious/15 text-status-serious',
  critical: 'bg-status-critical/10 text-status-critical',
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STYLES[level]}`}
    >
      {level}
    </span>
  )
}
