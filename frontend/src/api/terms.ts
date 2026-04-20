import axios from 'axios'
import type { Term, TermDetail, TermsResponse, VoteResponse, CreateTermPayload, SuggestionResponse } from '../types'

export async function fetchTerms(params: {
  q?: string
  status?: string
  category?: string
  limit?: number
  offset?: number
}): Promise<TermsResponse> {
  const cleanParams = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== '')
  )
  const res = await axios.get<TermsResponse>('/api/v1/terms', { params: cleanParams })
  return res.data
}

export async function fetchTermDetail(id: string): Promise<TermDetail> {
  const res = await axios.get<TermDetail>(`/api/v1/terms/${id}`)
  return res.data
}

export async function addTerm(payload: CreateTermPayload): Promise<Term> {
  const res = await axios.post<Term>('/api/v1/terms', payload)
  return res.data
}

export async function voteTerm(id: string): Promise<VoteResponse> {
  const res = await axios.post<VoteResponse>(`/api/v1/terms/${id}/vote`)
  return res.data
}

export async function suggestDefinition(
  id: string,
  definition: string,
  comment?: string
): Promise<SuggestionResponse> {
  const res = await axios.post<SuggestionResponse>(`/api/v1/terms/${id}/suggest`, {
    definition,
    ...(comment ? { comment } : {}),
  })
  return res.data
}

export async function fetchSuggestions(id: string): Promise<SuggestionResponse[]> {
  const res = await axios.get<SuggestionResponse[]>(`/api/v1/terms/${id}/suggestions`)
  return res.data
}

export async function acceptSuggestion(
  termId: string,
  suggestionId: string,
  replace = false,
  mergedDefinition?: string
): Promise<Term> {
  const body = mergedDefinition ? { merged_definition: mergedDefinition } : {}
  const res = await axios.post<Term>(
    `/api/v1/terms/${termId}/suggestions/${suggestionId}/accept`,
    body,
    { params: replace && !mergedDefinition ? { replace: true } : {} }
  )
  return res.data
}

export async function rejectSuggestion(termId: string, suggestionId: string): Promise<void> {
  await axios.post(`/api/v1/terms/${termId}/suggestions/${suggestionId}/reject`)
}
