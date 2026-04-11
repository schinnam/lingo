import { useState } from 'react'
import type { TermDetail as TermDetailType } from '../types'
import type { Features } from '../api/features'
import { StatusBadge } from './StatusBadge'

interface TermDetailProps {
  term: TermDetailType
  features: Features
  onClose: () => void
  onVote: (id: string) => void
  onDispute: (id: string, comment?: string) => void
}

export function TermDetail({ term, features, onClose, onVote, onDispute }: TermDetailProps) {
  const [disputeOpen, setDisputeOpen] = useState(false)
  const [comment, setComment] = useState('')

  function handleDisputeSubmit() {
    onDispute(term.id, comment.trim() || undefined)
    setDisputeOpen(false)
    setComment('')
  }

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
        {features.voting && <StatusBadge status={term.status} isStale={features.staleness ? term.is_stale : false} />}
        {features.voting && (
          <span className="text-sm text-gray-500">👍 <span>{term.vote_count}</span></span>
        )}
      </div>

      <p className="text-sm text-gray-800 mb-4">{term.definition}</p>

      {term.owner && (
        <p className="text-xs text-gray-500 mb-2">Owner: <span>@{term.owner.display_name}</span></p>
      )}

      {features.relationships && (term.relationships ?? []).length > 0 && (
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

      {features.voting && (
        <div className="mt-auto pt-4 border-t border-gray-100">
          {disputeOpen ? (
            <div className="flex flex-col gap-2">
              <label htmlFor="dispute-comment" className="text-xs text-gray-600 font-medium">
                Add a comment (optional)
              </label>
              <textarea
                id="dispute-comment"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Explain why this definition is incorrect or outdated…"
                rows={3}
                maxLength={500}
                className="w-full text-sm border border-gray-300 rounded-md p-2 resize-none focus:outline-none focus:ring-2 focus:ring-orange-400"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleDisputeSubmit}
                  aria-label="Submit dispute"
                  className="flex-1 px-3 py-2 bg-orange-500 text-white text-sm rounded-md hover:bg-orange-600 transition-colors"
                >
                  Submit Dispute
                </button>
                <button
                  onClick={() => { setDisputeOpen(false); setComment('') }}
                  aria-label="Cancel dispute"
                  className="flex-1 px-3 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={() => onVote(term.id)}
                aria-label="Vote for this term"
                className="flex-1 px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
              >
                👍 Vote
              </button>
              <button
                onClick={() => setDisputeOpen(true)}
                aria-label="Dispute this term"
                className="flex-1 px-3 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50 transition-colors"
              >
                ⚑ Dispute
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
