import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { TermDetail } from '../components/TermDetail'
import type { TermDetail as TermDetailType } from '../types'
import type { Features } from '../api/features'

const allFeatures: Features = {
  discovery: true,
  relationships: true,
  voting: true,
  staleness: true,
}

const mockTerm: TermDetailType = {
  id: 'abc-123',
  name: 'BART',
  full_name: 'Business Arts Resource Tool',
  definition: 'A centralized resource hub for business operations.',
  category: 'Operations',
  status: 'official',
  vote_count: 12,
  is_stale: false,
  owner: { display_name: 'Alice' },
  last_confirmed_at: '2026-03-20T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-03-20T00:00:00Z',
  version: 1,
  relationships: [
    {
      id: 'rel-1',
      relationship_type: 'depends_on',
      related_term: { id: 'def-456', name: 'FMTL', definition: 'Field Mgmt Tool' },
    },
  ],
}

describe('TermDetail', () => {
  it('renders term name as heading', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onDispute={() => {}} />)
    expect(screen.getByRole('heading', { name: 'BART' })).toBeInTheDocument()
  })

  it('renders full_name', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onDispute={() => {}} />)
    expect(screen.getByText('Business Arts Resource Tool')).toBeInTheDocument()
  })

  it('renders definition', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onDispute={() => {}} />)
    expect(screen.getByText('A centralized resource hub for business operations.')).toBeInTheDocument()
  })

  it('renders status badge', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onDispute={() => {}} />)
    expect(screen.getByText('Official')).toBeInTheDocument()
  })

  it('renders vote count', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onDispute={() => {}} />)
    expect(screen.getByText('12')).toBeInTheDocument()
  })

  it('renders owner display name', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onDispute={() => {}} />)
    expect(screen.getByText('@Alice')).toBeInTheDocument()
  })

  it('renders related term', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onDispute={() => {}} />)
    expect(screen.getByText('FMTL')).toBeInTheDocument()
  })

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn()
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={onClose} onVote={() => {}} onDispute={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /close/i }))
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onVote when Vote button clicked', () => {
    const onVote = vi.fn()
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={onVote} onDispute={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /vote/i }))
    expect(onVote).toHaveBeenCalledWith('abc-123')
  })

  it('calls onDispute when Submit Dispute button clicked', () => {
    const onDispute = vi.fn()
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onDispute={onDispute} />)
    
    // Step 1: Click Dispute to open the form
    fireEvent.click(screen.getByRole('button', { name: /dispute this term/i }))
    
    // Step 2: Click Submit Dispute
    fireEvent.click(screen.getByRole('button', { name: /submit dispute/i }))
    
    expect(onDispute).toHaveBeenCalledWith('abc-123', undefined)
  })

  it('calls onDispute with comment when Submit Dispute button clicked', () => {
    const onDispute = vi.fn()
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onDispute={onDispute} />)
    
    fireEvent.click(screen.getByRole('button', { name: /dispute this term/i }))
    
    const textarea = screen.getByPlaceholderText(/explain why this definition is incorrect/i)
    fireEvent.change(textarea, { target: { value: 'Inaccurate definition' } })
    
    fireEvent.click(screen.getByRole('button', { name: /submit dispute/i }))
    
    expect(onDispute).toHaveBeenCalledWith('abc-123', 'Inaccurate definition')
  })

  it('has role=dialog and focus-able panel', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onDispute={() => {}} />)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })
})
