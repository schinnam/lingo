import type { TermDetail as TermDetailType } from '../types'
import { StatusBadge } from './StatusBadge'

interface TermDetailProps {
  term: TermDetailType
  onClose: () => void
  onVote: (id: string) => void
  onDispute: (id: string) => void
}

export function TermDetail({ term, onClose, onVote, onDispute }: TermDetailProps) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="term-detail-heading"
      className="h-full flex flex-col bg-white border-l border-gray-200 p-4"
    >
      <div className="flex items-start justify-between mb-4">
        <h2 id="term-detail-heading" className="font-mono font-bold text-lg text-gray-900">
          {term.name}
        </h2>
        <button
          onClick={onClose}
          aria-label="Close"
          className="text-gray-400 hover:text-gray-600 text-xl leading-none"
        >
          ×
        </button>
      </div>

      {term.full_name && (
        <p className="text-sm text-gray-500 mb-3">{term.full_name}</p>
      )}

      <div className="flex items-center gap-3 mb-4">
        <StatusBadge status={term.status} isStale={term.is_stale} />
        <span className="text-sm text-gray-500">👍 <span>{term.vote_count}</span></span>
      </div>

      <p className="text-sm text-gray-800 mb-4">{term.definition}</p>

      {term.owner && (
        <p className="text-xs text-gray-500 mb-2">Owner: <span>@{term.owner.display_name}</span></p>
      )}

      {(term.relationships ?? []).length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-gray-500 uppercase mb-1">Related Terms</p>
          <ul className="space-y-1">
            {(term.relationships ?? []).map((rel) => (
              <li key={rel.id} className="text-sm">
                <span className="font-mono font-bold text-gray-800">{rel.related_term.name}</span>
                <span className="text-gray-400 ml-1 text-xs">({rel.relationship_type})</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex gap-2 mt-auto pt-4 border-t border-gray-100">
        <button
          onClick={() => onVote(term.id)}
          aria-label="Vote for this term"
          className="flex-1 px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
        >
          👍 Vote
        </button>
        <button
          onClick={() => onDispute(term.id)}
          aria-label="Dispute this term"
          className="flex-1 px-3 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50 transition-colors"
        >
          ⚑ Dispute
        </button>
      </div>
    </div>
  )
}
