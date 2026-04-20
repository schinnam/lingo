import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { TermRow } from '../components/TermRow'
import type { Term } from '../types'

const mockTerm: Term = {
  id: 'abc-123',
  name: 'BART',
  full_name: 'Business Arts Resource Tool',
  definition: 'A centralized resource hub.',
  category: 'Operations',
  status: 'official',
  vote_count: 12,
  is_stale: false,
  owner: { display_name: 'Alice' },
  last_confirmed_at: '2026-03-20T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-03-20T00:00:00Z',
  version: 1,
  extra_definitions: [],
}

describe('TermRow', () => {
  it('renders term name in monospace bold', () => {
    render(<TermRow term={mockTerm} isSelected={false} onClick={() => {}} />)
    const name = screen.getByText('BART')
    expect(name).toBeInTheDocument()
    expect(name).toHaveClass('font-mono', 'font-bold')
  })

  it('renders status badge', () => {
    render(<TermRow term={mockTerm} isSelected={false} onClick={() => {}} />)
    expect(screen.getByText('Official')).toBeInTheDocument()
  })

  it('renders vote count', () => {
    render(<TermRow term={mockTerm} isSelected={false} onClick={() => {}} />)
    expect(screen.getByText('12')).toBeInTheDocument()
  })

  it('renders category', () => {
    render(<TermRow term={mockTerm} isSelected={false} onClick={() => {}} />)
    expect(screen.getByText('Operations')).toBeInTheDocument()
  })

  it('calls onClick when clicked', () => {
    const onClick = vi.fn()
    render(<TermRow term={mockTerm} isSelected={false} onClick={onClick} />)
    fireEvent.click(screen.getByRole('row'))
    expect(onClick).toHaveBeenCalledWith(mockTerm)
  })

  it('has selected highlight when isSelected=true', () => {
    render(<TermRow term={mockTerm} isSelected={true} onClick={() => {}} />)
    expect(screen.getByRole('row')).toHaveClass('bg-blue-50')
  })

  it('shows stale chip when is_stale=true', () => {
    const staleTerm = { ...mockTerm, is_stale: true }
    render(<TermRow term={staleTerm} isSelected={false} onClick={() => {}} />)
    expect(screen.getByText('⚠ Stale')).toBeInTheDocument()
  })

  it('has correct aria role and is keyboard accessible', () => {
    render(<TermRow term={mockTerm} isSelected={false} onClick={() => {}} />)
    const row = screen.getByRole('row')
    expect(row).toHaveAttribute('tabIndex', '0')
  })
})
