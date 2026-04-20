import { useState, useCallback, useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SearchBar } from './components/SearchBar'
import { StatusFilter } from './components/StatusFilter'
import { TermRow } from './components/TermRow'
import { TermDetail } from './components/TermDetail'
import { AddTermModal } from './components/AddTermModal'
import { DevModeBanner } from './components/DevModeBanner'
import {
  useTerms,
  useTermDetail,
  useAddTerm,
  useVoteTerm,
  useSuggestDefinition,
  useSuggestions,
  useAcceptSuggestion,
  useRejectSuggestion,
} from './hooks/useTerms'
import { useFeatures } from './hooks/useFeatures'
import { fetchCurrentUser, type CurrentUser } from './api/auth'
import type { Term, TermStatus } from './types'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000 } },
})

function isDevMode(): boolean {
  return document.querySelector('meta[name="lingo-dev-mode"]') !== null
}

function AppInner() {
  const [authStatus, setAuthStatus] = useState<'loading' | 'authed'>('loading')
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<TermStatus | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [addModalOpen, setAddModalOpen] = useState(false)

  const features = useFeatures()
  const { data, isLoading, isError } = useTerms({ q: search, status: features.voting ? statusFilter : null })
  const { data: detail } = useTermDetail(selectedId)
  const addTerm = useAddTerm()
  const voteTerm = useVoteTerm()
  const suggestDefinition = useSuggestDefinition()
  const { data: suggestions } = useSuggestions(selectedId)
  const acceptSuggestion = useAcceptSuggestion()
  const rejectSuggestion = useRejectSuggestion()

  const terms = data?.items ?? []

  const statusCounts = data?.counts_by_status ?? {}
  const counts = {
    all: data?.total ?? 0,
    official: statusCounts['official'] ?? 0,
    community: statusCounts['community'] ?? 0,
    pending: statusCounts['pending'] ?? 0,
    suggested: statusCounts['suggested'] ?? 0,
  }

  useEffect(() => {
    fetchCurrentUser()
      .then((user) => {
        setCurrentUser(user)
        setAuthStatus('authed')
      })
      .catch(() => {
        // The 401 interceptor in api/auth.ts handles the redirect to /login.
      })
  }, [])

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      const isInput =
        document.activeElement?.tagName === 'INPUT' ||
        document.activeElement?.tagName === 'TEXTAREA'
      if ((e.key === '/' || (e.key === 'k' && (e.metaKey || e.ctrlKey))) && !isInput) {
        e.preventDefault()
        document.querySelector<HTMLInputElement>('input[type="search"]')?.focus()
      }
      if (e.key === 'Escape' && selectedId) {
        setSelectedId(null)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [selectedId])

  const handleRowClick = useCallback((term: Term) => {
    setSelectedId((prev) => (prev === term.id ? null : term.id))
  }, [])

  async function handleAddTerm(payload: Parameters<typeof addTerm.mutateAsync>[0]) {
    await addTerm.mutateAsync(payload)
    setAddModalOpen(false)
  }

  if (authStatus === 'loading') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <span className="text-gray-400 text-sm">Loading…</span>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <DevModeBanner show={isDevMode()} />

      <header className="bg-white border-b border-gray-200 px-8 py-3 flex items-center gap-6">
        <h1 className="text-xl font-bold font-mono text-gray-900 whitespace-nowrap">Lingo</h1>
        <SearchBar value={search} onChange={setSearch} />
        {currentUser?.role === 'admin' && (
          <a
            href="/admin"
            className="whitespace-nowrap text-sm text-gray-500 hover:text-gray-900"
          >
            Admin
          </a>
        )}
        <button
          onClick={() => setAddModalOpen(true)}
          className="whitespace-nowrap px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
          aria-label="Add term"
        >
          + Add
        </button>
      </header>

      {features.voting && (
        <div className="bg-white border-b border-gray-200 px-8 py-2">
          <StatusFilter active={statusFilter} counts={counts} onChange={setStatusFilter} />
        </div>
      )}

      <main className="flex flex-1 overflow-hidden">
        <div className={`flex-1 overflow-y-auto ${selectedId ? 'hidden md:block' : ''}`}>
          {isLoading ? (
            <div className="flex items-center justify-center py-16 text-gray-400 text-sm">
              Loading…
            </div>
          ) : isError ? (
            <div className="flex items-center justify-center py-16 text-red-400 text-sm">
              Could not load terms. Check your connection and try again.
            </div>
          ) : terms.length === 0 ? (
            <div className="flex items-center justify-center py-16 text-gray-400 text-sm">
              No terms found.
            </div>
          ) : (
            <table className="w-full border-collapse">
              <thead className="sr-only">
                <tr>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Votes</th>
                  <th>Category</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {terms.map((term) => (
                  <TermRow
                    key={term.id}
                    term={term}
                    isSelected={selectedId === term.id}
                    onClick={handleRowClick}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>

        {selectedId && detail && (
          <aside className="w-full md:w-96 border-l border-gray-200 overflow-y-auto">
            <TermDetail
              term={detail}
              features={features}
              onClose={() => setSelectedId(null)}
              onVote={(id) => voteTerm.mutate(id)}
              onSuggest={(id, definition, comment) =>
                suggestDefinition.mutate({ id, definition, comment })
              }
              suggestions={suggestions}
              onAcceptSuggestion={(termId, suggestionId, replace, mergedDefinition) =>
                acceptSuggestion.mutate({ termId, suggestionId, replace, mergedDefinition })
              }
              onRejectSuggestion={(termId, suggestionId) =>
                rejectSuggestion.mutate({ termId, suggestionId })
              }
            />
          </aside>
        )}
      </main>

      <AddTermModal
        isOpen={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        onSubmit={handleAddTerm}
        isPending={addTerm.isPending}
      />
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  )
}
