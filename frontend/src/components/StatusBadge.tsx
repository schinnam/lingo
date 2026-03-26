import type { TermStatus } from '../types'

const statusStyles: Record<TermStatus, string> = {
  official: 'bg-emerald-100 text-emerald-800',
  community: 'bg-amber-100 text-amber-800',
  pending: 'bg-gray-200 text-gray-700',
  suggested: 'bg-gray-100 text-gray-400',
}

const statusLabels: Record<TermStatus, string> = {
  official: 'Official',
  community: 'Community',
  pending: 'Pending',
  suggested: 'Suggested',
}

interface StatusBadgeProps {
  status: TermStatus
  isStale?: boolean
}

export function StatusBadge({ status, isStale = false }: StatusBadgeProps) {
  return (
    <span className="inline-flex items-center gap-1">
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium uppercase ${statusStyles[status]}`}
        aria-label={`Status: ${statusLabels[status]}`}
      >
        {statusLabels[status]}
      </span>
      {isStale && (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
          ⚠ Stale
        </span>
      )}
    </span>
  )
}
