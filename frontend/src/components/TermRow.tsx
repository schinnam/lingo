import type { Term } from '../types'
import { StatusBadge } from './StatusBadge'

interface TermRowProps {
  term: Term
  isSelected: boolean
  onClick: (term: Term) => void
}

export function TermRow({ term, isSelected, onClick }: TermRowProps) {
  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onClick(term)
    }
  }

  return (
    <tr
      role="row"
      tabIndex={0}
      onClick={() => onClick(term)}
      onKeyDown={handleKeyDown}
      className={`cursor-pointer hover:bg-gray-50 transition-colors ${isSelected ? 'bg-blue-50' : ''}`}
    >
      <td className="px-3 py-2 whitespace-nowrap">
        <span className="font-mono font-bold text-sm text-gray-900">{term.name}</span>
      </td>
      <td className="px-3 py-2 whitespace-nowrap">
        <StatusBadge status={term.status} isStale={term.is_stale} />
      </td>
      <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500">
        <span>👍 </span>
        <span>{term.vote_count}</span>
      </td>
      <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500">
        {term.category ?? '—'}
      </td>
    </tr>
  )
}
