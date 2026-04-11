import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchTerms, fetchTermDetail, addTerm, voteTerm, disputeTerm } from '../api/terms'
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

export function useDisputeTerm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, comment }: { id: string; comment?: string }) => disputeTerm(id, comment),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ['term', id] })
      qc.invalidateQueries({ queryKey: ['terms'] })
    },
  })
}
