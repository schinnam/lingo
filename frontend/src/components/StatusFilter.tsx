import type { TermStatus } from '../types'

interface StatusCounts {
  all: number
  official: number
  community: number
  pending: number
  suggested: number
}

interface StatusFilterProps {
  active: TermStatus | null
  counts: StatusCounts
  onChange: (status: TermStatus | null) => void
}

const filters: Array<{ key: TermStatus | null; label: string; countKey: keyof StatusCounts | 'all' }> = [
  { key: null, label: 'All', countKey: 'all' },
  { key: 'official', label: 'Official', countKey: 'official' },
  { key: 'community', label: 'Community', countKey: 'community' },
  { key: 'pending', label: 'Pending', countKey: 'pending' },
  { key: 'suggested', label: 'Suggested', countKey: 'suggested' },
]

export function StatusFilter({ active, counts, onChange }: StatusFilterProps) {
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by status">
      {filters.map(({ key, label, countKey }) => {
        const count = counts[countKey as keyof StatusCounts]
        const isActive = active === key
        return (
          <button
            key={label}
            aria-pressed={isActive}
            onClick={() => onChange(isActive ? null : key)}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              isActive
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {label} ({count})
          </button>
        )
      })}
    </div>
  )
}
