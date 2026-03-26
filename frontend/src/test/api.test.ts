import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

vi.mock('axios')

// We test the API module functions directly
import { fetchTerms, fetchTermDetail, addTerm, voteTerm, disputeTerm } from '../api/terms'

const mockedAxios = vi.mocked(axios, true)

describe('API: fetchTerms', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls GET /api/v1/terms with no filters', async () => {
    mockedAxios.get = vi.fn().mockResolvedValue({
      data: { items: [], total: 0, offset: 0, limit: 20 },
    })
    const result = await fetchTerms({})
    expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/terms', { params: {} })
    expect(result.total).toBe(0)
  })

  it('passes status and q filters as params', async () => {
    mockedAxios.get = vi.fn().mockResolvedValue({
      data: { items: [], total: 0, offset: 0, limit: 20 },
    })
    await fetchTerms({ status: 'official', q: 'BART' })
    expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/terms', {
      params: { status: 'official', q: 'BART' },
    })
  })
})

describe('API: fetchTermDetail', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls GET /api/v1/terms/:id', async () => {
    mockedAxios.get = vi.fn().mockResolvedValue({ data: { id: 'abc-123' } })
    const result = await fetchTermDetail('abc-123')
    expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/terms/abc-123')
    expect(result.id).toBe('abc-123')
  })
})

describe('API: addTerm', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls POST /api/v1/terms with payload', async () => {
    mockedAxios.post = vi.fn().mockResolvedValue({ data: { id: 'new-123' } })
    const payload = { name: 'BART', definition: 'A resource hub.' }
    const result = await addTerm(payload)
    expect(mockedAxios.post).toHaveBeenCalledWith('/api/v1/terms', payload)
    expect(result.id).toBe('new-123')
  })
})

describe('API: voteTerm', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls POST /api/v1/terms/:id/vote', async () => {
    mockedAxios.post = vi.fn().mockResolvedValue({ data: { vote_count: 5 } })
    const result = await voteTerm('abc-123')
    expect(mockedAxios.post).toHaveBeenCalledWith('/api/v1/terms/abc-123/vote')
    expect(result.vote_count).toBe(5)
  })
})

describe('API: disputeTerm', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls POST /api/v1/terms/:id/dispute', async () => {
    mockedAxios.post = vi.fn().mockResolvedValue({ data: {} })
    await disputeTerm('abc-123')
    expect(mockedAxios.post).toHaveBeenCalledWith('/api/v1/terms/abc-123/dispute')
  })
})
