import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { StatusBadge } from '../components/StatusBadge'

describe('StatusBadge', () => {
  it('renders Official with green styling', () => {
    render(<StatusBadge status="official" />)
    const badge = screen.getByText('Official')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveAttribute('aria-label', 'Status: Official')
    expect(badge).toHaveClass('bg-emerald-100', 'text-emerald-800')
  })

  it('renders Community with amber styling', () => {
    render(<StatusBadge status="community" />)
    const badge = screen.getByText('Community')
    expect(badge).toHaveClass('bg-amber-100', 'text-amber-800')
  })

  it('renders Pending with gray styling', () => {
    render(<StatusBadge status="pending" />)
    const badge = screen.getByText('Pending')
    expect(badge).toHaveClass('bg-gray-200', 'text-gray-700')
  })

  it('renders Suggested with light gray styling', () => {
    render(<StatusBadge status="suggested" />)
    const badge = screen.getByText('Suggested')
    expect(badge).toHaveClass('bg-gray-100', 'text-gray-400')
  })

  it('renders stale chip when isStale=true', () => {
    render(<StatusBadge status="official" isStale />)
    expect(screen.getByText('⚠ Stale')).toBeInTheDocument()
    const staleChip = screen.getByText('⚠ Stale')
    expect(staleChip).toHaveClass('bg-red-100', 'text-red-800')
  })

  it('does not render stale chip when isStale=false', () => {
    render(<StatusBadge status="official" isStale={false} />)
    expect(screen.queryByText('⚠ Stale')).not.toBeInTheDocument()
  })
})
