export type TermStatus = 'suggested' | 'pending' | 'community' | 'official'

export interface Term {
  id: string
  name: string
  full_name: string | null
  definition: string
  category: string | null
  status: TermStatus
  vote_count: number
  is_stale: boolean
  owner: { display_name: string } | null
  last_confirmed_at: string | null
  created_at: string
  updated_at: string
  version: number
}

export interface TermDetail extends Term {
  relationships: Array<{
    id: string
    relationship_type: string
    related_term: { id: string; name: string; definition: string }
  }>
}

export interface TermsResponse {
  items: Term[]
  total: number
  offset: number
  limit: number
}

export interface CreateTermPayload {
  name: string
  definition: string
  full_name?: string
  category?: string
}
