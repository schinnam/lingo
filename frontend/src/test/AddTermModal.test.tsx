import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AddTermModal } from '../components/AddTermModal'

describe('AddTermModal', () => {
  it('renders modal with form fields when open', () => {
    render(<AddTermModal isOpen={true} onClose={() => {}} onSubmit={async () => {}} />)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByLabelText(/term name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/definition/i)).toBeInTheDocument()
  })

  it('does not render when isOpen=false', () => {
    render(<AddTermModal isOpen={false} onClose={() => {}} onSubmit={async () => {}} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('validates required fields — shows error when name is empty on submit', async () => {
    render(<AddTermModal isOpen={true} onClose={() => {}} onSubmit={async () => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /add term/i }))
    await waitFor(() => {
      expect(screen.getByText(/name is required/i)).toBeInTheDocument()
    })
  })

  it('validates required fields — shows error when definition is empty on submit', async () => {
    render(<AddTermModal isOpen={true} onClose={() => {}} onSubmit={async () => {}} />)
    fireEvent.change(screen.getByLabelText(/term name/i), { target: { value: 'BART' } })
    fireEvent.click(screen.getByRole('button', { name: /add term/i }))
    await waitFor(() => {
      expect(screen.getByText(/definition is required/i)).toBeInTheDocument()
    })
  })

  it('calls onSubmit with form data when valid', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<AddTermModal isOpen={true} onClose={() => {}} onSubmit={onSubmit} />)
    fireEvent.change(screen.getByLabelText(/term name/i), { target: { value: 'BART' } })
    fireEvent.change(screen.getByLabelText(/definition/i), { target: { value: 'Business Arts Resource Tool' } })
    fireEvent.click(screen.getByRole('button', { name: /add term/i }))
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        name: 'BART',
        definition: 'Business Arts Resource Tool',
        full_name: '',
        category: '',
      })
    })
  })

  it('calls onClose when Cancel button clicked', () => {
    const onClose = vi.fn()
    render(<AddTermModal isOpen={true} onClose={onClose} onSubmit={async () => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onClose).toHaveBeenCalled()
  })

  it('renders optional full_name and category fields', () => {
    render(<AddTermModal isOpen={true} onClose={() => {}} onSubmit={async () => {}} />)
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/category/i)).toBeInTheDocument()
  })
})
