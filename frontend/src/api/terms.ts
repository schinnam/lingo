import axios from 'axios'
import type { Term, TermDetail, TermsResponse, CreateTermPayload } from '../types'

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

export async function voteTerm(id: string): Promise<Term> {
  const res = await axios.post<Term>(`/api/v1/terms/${id}/vote`)
  return res.data
}

export async function disputeTerm(id: string): Promise<void> {
  await axios.post(`/api/v1/terms/${id}/dispute`)
}
