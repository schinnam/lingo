import { useState } from 'react'
import type { TermDetail as TermDetailType, SuggestionResponse } from '../types'
import type { Features } from '../api/features'
import { StatusBadge } from './StatusBadge'

interface TermDetailProps {
  term: TermDetailType
  features: Features
  onClose: () => void
  onVote: (id: string) => void
  onSuggest: (id: string, definition: string, comment?: string) => void
  suggestions?: SuggestionResponse[]
  onAcceptSuggestion?: (termId: string, suggestionId: string, replace: boolean) => void
  onRejectSuggestion?: (termId: string, suggestionId: string) => void
}

export function TermDetail({
  term,
  features,
  onClose,
  onVote,
  onSuggest,
  suggestions,
  onAcceptSuggestion,
  onRejectSuggestion,
}: TermDetailProps) {
  const [suggestOpen, setSuggestOpen] = useState(false)
  const [suggestedDefinition, setSuggestedDefinition] = useState('')
  const [comment, setComment] = useState('')

  function handleSuggestSubmit() {
    if (!suggestedDefinition.trim()) return
    onSuggest(term.id, suggestedDefinition.trim(), comment.trim() || undefined)
    setSuggestOpen(false)
    setSuggestedDefinition('')
    setComment('')
  }

  const pendingSuggestions = suggestions?.filter((s) => s.status === 'pending') ?? []

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

      <div className="mb-4">
        <p className="text-sm text-gray-800">{term.definition}</p>
        {term.extra_definitions.length > 0 && (
          <ol className="mt-2 space-y-1 list-decimal list-inside">
            {term.extra_definitions.map((def, i) => (
              <li key={i} className="text-sm text-gray-600">{def}</li>
            ))}
          </ol>
        )}
      </div>

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

      {pendingSuggestions.length > 0 && (
        <div className="mb-4 border border-blue-100 rounded-md p-3 bg-blue-50">
          <p className="text-xs font-medium text-blue-700 uppercase mb-2">Pending Suggestions</p>
          <ul className="space-y-3">
            {pendingSuggestions.map((s) => (
              <li key={s.id} className="text-sm">
                <p className="text-gray-800 mb-1">{s.definition}</p>
                {s.comment && <p className="text-xs text-gray-500 italic mb-2">{s.comment}</p>}
                {(onAcceptSuggestion || onRejectSuggestion) && (
                  <div className="flex gap-2">
                    {onAcceptSuggestion && (
                      <>
                        <button
                          onClick={() => onAcceptSuggestion(term.id, s.id, false)}
                          className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700"
                          aria-label="Add as extra definition"
                        >
                          + Add definition
                        </button>
                        <button
                          onClick={() => onAcceptSuggestion(term.id, s.id, true)}
                          className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                          aria-label="Replace primary definition"
                        >
                          Replace primary
                        </button>
                      </>
                    )}
                    {onRejectSuggestion && (
                      <button
                        onClick={() => onRejectSuggestion(term.id, s.id)}
                        className="text-xs px-2 py-1 border border-gray-300 text-gray-600 rounded hover:bg-gray-100"
                        aria-label="Reject suggestion"
                      >
                        Reject
                      </button>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {features.voting && (
        <div className="mt-auto pt-4 border-t border-gray-100">
          {suggestOpen ? (
            <div className="flex flex-col gap-2">
              <label htmlFor="suggest-definition" className="text-xs text-gray-600 font-medium">
                Suggested definition <span className="text-red-500">*</span>
              </label>
              <textarea
                id="suggest-definition"
                value={suggestedDefinition}
                onChange={(e) => setSuggestedDefinition(e.target.value)}
                placeholder="Enter the definition you'd like to suggest…"
                rows={3}
                maxLength={2000}
                className="w-full text-sm border border-gray-300 rounded-md p-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <label htmlFor="suggest-comment" className="text-xs text-gray-600 font-medium">
                Comment (optional)
              </label>
              <textarea
                id="suggest-comment"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Why are you suggesting this change?"
                rows={2}
                maxLength={500}
                className="w-full text-sm border border-gray-300 rounded-md p-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSuggestSubmit}
                  disabled={!suggestedDefinition.trim()}
                  aria-label="Submit suggestion"
                  className="flex-1 px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Submit Suggestion
                </button>
                <button
                  onClick={() => { setSuggestOpen(false); setSuggestedDefinition(''); setComment('') }}
                  aria-label="Cancel suggestion"
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
                onClick={() => setSuggestOpen(true)}
                aria-label="Suggest a change to this term"
                className="flex-1 px-3 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50 transition-colors"
              >
                ✏ Suggest Change
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
