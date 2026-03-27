import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { StatusFilter } from '../components/StatusFilter'
import type { TermStatus } from '../types'

const counts = {
  all: 104,
  official: 62,
  community: 21,
  pending: 8,
  suggested: 23,
}

describe('StatusFilter', () => {
  it('renders All filter pill as active by default', () => {
    render(<StatusFilter active={null} counts={counts} onChange={() => {}} />)
    const allBtn = screen.getByText('All (104)')
    expect(allBtn).toBeInTheDocument()
    expect(allBtn.closest('button')).toHaveAttribute('aria-pressed', 'true')
  })

  it('renders status pills: Official, Community, Pending, Suggested', () => {
    render(<StatusFilter active={null} counts={counts} onChange={() => {}} />)
    expect(screen.getByText('Official (62)')).toBeInTheDocument()
    expect(screen.getByText('Community (21)')).toBeInTheDocument()
    expect(screen.getByText('Pending (8)')).toBeInTheDocument()
    expect(screen.getByText('Suggested (23)')).toBeInTheDocument()
  })

  it('calls onChange with status when pill clicked', () => {
    const onChange = vi.fn()
    render(<StatusFilter active={null} counts={counts} onChange={onChange} />)
    fireEvent.click(screen.getByText('Official (62)'))
    expect(onChange).toHaveBeenCalledWith('official')
  })

  it('calls onChange with null when active pill clicked (deselect)', () => {
    const onChange = vi.fn()
    render(<StatusFilter active={'official' as TermStatus} counts={counts} onChange={onChange} />)
    fireEvent.click(screen.getByText('Official (62)'))
    expect(onChange).toHaveBeenCalledWith(null)
  })

  it('marks active filter pill with aria-pressed=true', () => {
    render(<StatusFilter active={'community' as TermStatus} counts={counts} onChange={() => {}} />)
    const btn = screen.getByText('Community (21)').closest('button')
    expect(btn).toHaveAttribute('aria-pressed', 'true')
  })
})
