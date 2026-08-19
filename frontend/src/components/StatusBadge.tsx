const NEUTRAL = 'bg-gray-100 text-gray-700'
const POSITIVE = 'bg-emerald-50 text-emerald-700'
const NEGATIVE = 'bg-gray-200 text-gray-500'

const OVERRIDES: Record<string, string> = {
  active: POSITIVE,
  completed: POSITIVE,
  terminated: NEGATIVE,
  dismissed: NEGATIVE,
  cancelled: NEGATIVE,
}

/** A neutral status pill for anything that isn't a RiskLevel (which uses
 * the reserved status palette in RiskBadge instead). */
export function StatusBadge({ value }: { value: string }) {
  const className = OVERRIDES[value] ?? NEUTRAL
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${className}`}
    >
      {value.replaceAll('_', ' ')}
    </span>
  )
}
