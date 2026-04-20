import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchTerms,
  fetchTermDetail,
  addTerm,
  voteTerm,
  suggestDefinition,
  fetchSuggestions,
  acceptSuggestion,
  rejectSuggestion,
} from '../api/terms'
import type { TermStatus, CreateTermPayload } from '../types'

export function useTerms(params: { q?: string; status?: TermStatus | null; category?: string }) {
  const cleanParams = {
    ...(params.q ? { q: params.q } : {}),
    ...(params.status ? { status: params.status } : {}),
    ...(params.category ? { category: params.category } : {}),
  }
  return useQuery({
    queryKey: ['terms', cleanParams],
    queryFn: () => fetchTerms(cleanParams),
  })
}

export function useTermDetail(id: string | null) {
  return useQuery({
    queryKey: ['term', id],
    queryFn: () => fetchTermDetail(id!),
    enabled: !!id,
  })
}

export function useAddTerm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateTermPayload) => addTerm(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['terms'] }),
  })
}

export function useVoteTerm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => voteTerm(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['terms'] })
      qc.invalidateQueries({ queryKey: ['term', id] })
    },
  })
}

export function useSuggestDefinition() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, definition, comment }: { id: string; definition: string; comment?: string }) =>
      suggestDefinition(id, definition, comment),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ['suggestions', id] })
    },
  })
}

export function useSuggestions(termId: string | null) {
  return useQuery({
    queryKey: ['suggestions', termId],
    queryFn: () => fetchSuggestions(termId!),
    enabled: !!termId,
  })
}

export function useAcceptSuggestion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      termId,
      suggestionId,
      replace,
    }: {
      termId: string
      suggestionId: string
      replace?: boolean
    }) => acceptSuggestion(termId, suggestionId, replace),
    onSuccess: (_data, { termId }) => {
      qc.invalidateQueries({ queryKey: ['term', termId] })
      qc.invalidateQueries({ queryKey: ['terms'] })
      qc.invalidateQueries({ queryKey: ['suggestions', termId] })
    },
  })
}

export function useRejectSuggestion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ termId, suggestionId }: { termId: string; suggestionId: string }) =>
      rejectSuggestion(termId, suggestionId),
    onSuccess: (_data, { termId }) => {
      qc.invalidateQueries({ queryKey: ['suggestions', termId] })
    },
  })
}
