import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { SearchBar } from '../components/SearchBar'

describe('SearchBar', () => {
  it('renders a search input with placeholder', () => {
    render(<SearchBar value="" onChange={() => {}} />)
    const input = screen.getByPlaceholderText('Search terms...')
    expect(input).toBeInTheDocument()
  })

  it('renders with role="search" landmark', () => {
    render(<SearchBar value="" onChange={() => {}} />)
    expect(screen.getByRole('search')).toBeInTheDocument()
  })

  it('calls onChange when user types', () => {
    const onChange = vi.fn()
    render(<SearchBar value="" onChange={onChange} />)
    fireEvent.change(screen.getByPlaceholderText('Search terms...'), {
      target: { value: 'BART' },
    })
    expect(onChange).toHaveBeenCalledWith('BART')
  })

  it('displays current value', () => {
    render(<SearchBar value="FMTL" onChange={() => {}} />)
    expect(screen.getByDisplayValue('FMTL')).toBeInTheDocument()
  })
})
