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
  extra_definitions: [],
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
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onSuggest={() => {}} />)
    expect(screen.getByRole('heading', { name: 'BART' })).toBeInTheDocument()
  })

  it('renders full_name', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onSuggest={() => {}} />)
    expect(screen.getByText('Business Arts Resource Tool')).toBeInTheDocument()
  })

  it('renders definition', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onSuggest={() => {}} />)
    expect(screen.getByText('A centralized resource hub for business operations.')).toBeInTheDocument()
  })

  it('renders extra definitions when present', () => {
    const termWithExtras = {
      ...mockTerm,
      extra_definitions: ['Alternative meaning one', 'Alternative meaning two'],
    }
    render(<TermDetail term={termWithExtras} features={allFeatures} onClose={() => {}} onVote={() => {}} onSuggest={() => {}} />)
    expect(screen.getByText('Alternative meaning one')).toBeInTheDocument()
    expect(screen.getByText('Alternative meaning two')).toBeInTheDocument()
  })

  it('renders status badge', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onSuggest={() => {}} />)
    expect(screen.getByText('Official')).toBeInTheDocument()
  })

  it('renders vote count', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onSuggest={() => {}} />)
    expect(screen.getByText('12')).toBeInTheDocument()
  })

  it('renders owner display name', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onSuggest={() => {}} />)
    expect(screen.getByText('@Alice')).toBeInTheDocument()
  })

  it('renders related term', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onSuggest={() => {}} />)
    expect(screen.getByText('FMTL')).toBeInTheDocument()
  })

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn()
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={onClose} onVote={() => {}} onSuggest={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /close/i }))
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onVote when Vote button clicked', () => {
    const onVote = vi.fn()
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={onVote} onSuggest={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /vote for this term/i }))
    expect(onVote).toHaveBeenCalledWith('abc-123')
  })

  it('calls onSuggest when Submit Suggestion button clicked with definition', () => {
    const onSuggest = vi.fn()
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onSuggest={onSuggest} />)

    // Step 1: Click Suggest Change to open the form
    fireEvent.click(screen.getByRole('button', { name: /suggest a change to this term/i }))

    // Step 2: Fill in the required definition
    const definitionTextarea = screen.getByPlaceholderText(/enter the definition you'd like to suggest/i)
    fireEvent.change(definitionTextarea, { target: { value: 'A better definition' } })

    // Step 3: Submit
    fireEvent.click(screen.getByRole('button', { name: /submit suggestion/i }))

    expect(onSuggest).toHaveBeenCalledWith('abc-123', 'A better definition', undefined)
  })

  it('calls onSuggest with comment when both fields filled', () => {
    const onSuggest = vi.fn()
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onSuggest={onSuggest} />)

    fireEvent.click(screen.getByRole('button', { name: /suggest a change to this term/i }))

    const definitionTextarea = screen.getByPlaceholderText(/enter the definition you'd like to suggest/i)
    fireEvent.change(definitionTextarea, { target: { value: 'Better definition text' } })

    const commentTextarea = screen.getByPlaceholderText(/why are you suggesting this change/i)
    fireEvent.change(commentTextarea, { target: { value: 'More accurate wording' } })

    fireEvent.click(screen.getByRole('button', { name: /submit suggestion/i }))

    expect(onSuggest).toHaveBeenCalledWith('abc-123', 'Better definition text', 'More accurate wording')
  })

  it('does not call onSuggest when definition is empty', () => {
    const onSuggest = vi.fn()
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onSuggest={onSuggest} />)

    fireEvent.click(screen.getByRole('button', { name: /suggest a change to this term/i }))
    fireEvent.click(screen.getByRole('button', { name: /submit suggestion/i }))

    expect(onSuggest).not.toHaveBeenCalled()
  })

  it('has role=dialog and focus-able panel', () => {
    render(<TermDetail term={mockTerm} features={allFeatures} onClose={() => {}} onVote={() => {}} onSuggest={() => {}} />)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  describe('Mark Official button', () => {
    const communityTerm = { ...mockTerm, status: 'community' as const }

    it('shows Mark Official button for editors on non-official terms', () => {
      const onMarkOfficial = vi.fn()
      render(
        <TermDetail
          term={communityTerm}
          features={allFeatures}
          isEditor={true}
          onClose={() => {}}
          onVote={() => {}}
          onSuggest={() => {}}
          onMarkOfficial={onMarkOfficial}
        />
      )
      expect(screen.getByRole('button', { name: /mark this term as official/i })).toBeInTheDocument()
    })

    it('does not show Mark Official button for non-editors', () => {
      render(
        <TermDetail
          term={communityTerm}
          features={allFeatures}
          isEditor={false}
          onClose={() => {}}
          onVote={() => {}}
          onSuggest={() => {}}
          onMarkOfficial={vi.fn()}
        />
      )
      expect(screen.queryByRole('button', { name: /mark this term as official/i })).not.toBeInTheDocument()
    })

    it('does not show Mark Official button when term is already official', () => {
      render(
        <TermDetail
          term={mockTerm}
          features={allFeatures}
          isEditor={true}
          onClose={() => {}}
          onVote={() => {}}
          onSuggest={() => {}}
          onMarkOfficial={vi.fn()}
        />
      )
      expect(screen.queryByRole('button', { name: /mark this term as official/i })).not.toBeInTheDocument()
    })

    it('calls onMarkOfficial with term id when clicked', () => {
      const onMarkOfficial = vi.fn()
      render(
        <TermDetail
          term={communityTerm}
          features={allFeatures}
          isEditor={true}
          onClose={() => {}}
          onVote={() => {}}
          onSuggest={() => {}}
          onMarkOfficial={onMarkOfficial}
        />
      )
      fireEvent.click(screen.getByRole('button', { name: /mark this term as official/i }))
      expect(onMarkOfficial).toHaveBeenCalledWith('abc-123')
    })
  })

  describe('incorporate flow', () => {
    const pendingSuggestion = {
      id: 'sug-1',
      term_id: 'abc-123',
      definition: 'Extra detail to add',
      comment: null,
      suggested_by: 'user-1',
      status: 'pending' as const,
      created_at: null,
    }

    it('shows Edit & incorporate button for pending suggestions', () => {
      const onAccept = vi.fn()
      render(
        <TermDetail
          term={mockTerm}
          features={allFeatures}
          onClose={() => {}}
          onVote={() => {}}
          onSuggest={() => {}}
          suggestions={[pendingSuggestion]}
          onAcceptSuggestion={onAccept}
        />
      )
      expect(screen.getByRole('button', { name: /edit and incorporate suggestion/i })).toBeInTheDocument()
    })

    it('opens inline editor pre-populated with current definition on Edit & incorporate click', () => {
      render(
        <TermDetail
          term={mockTerm}
          features={allFeatures}
          onClose={() => {}}
          onVote={() => {}}
          onSuggest={() => {}}
          suggestions={[pendingSuggestion]}
          onAcceptSuggestion={() => {}}
        />
      )
      fireEvent.click(screen.getByRole('button', { name: /edit and incorporate suggestion/i }))
      const editor = screen.getByRole('textbox', { name: /edit to incorporate/i })
      expect(editor).toBeInTheDocument()
      expect((editor as HTMLTextAreaElement).value).toBe(mockTerm.definition)
    })

    it('calls onAcceptSuggestion with merged_definition on Save & Accept', () => {
      const onAccept = vi.fn()
      render(
        <TermDetail
          term={mockTerm}
          features={allFeatures}
          onClose={() => {}}
          onVote={() => {}}
          onSuggest={() => {}}
          suggestions={[pendingSuggestion]}
          onAcceptSuggestion={onAccept}
        />
      )
      fireEvent.click(screen.getByRole('button', { name: /edit and incorporate suggestion/i }))
      const editor = screen.getByRole('textbox', { name: /edit to incorporate/i })
      fireEvent.change(editor, { target: { value: 'Original plus extra detail' } })
      fireEvent.click(screen.getByRole('button', { name: /save incorporated definition/i }))
      expect(onAccept).toHaveBeenCalledWith('abc-123', 'sug-1', false, 'Original plus extra detail')
    })

    it('closes editor on Cancel without calling onAcceptSuggestion', () => {
      const onAccept = vi.fn()
      render(
        <TermDetail
          term={mockTerm}
          features={allFeatures}
          onClose={() => {}}
          onVote={() => {}}
          onSuggest={() => {}}
          suggestions={[pendingSuggestion]}
          onAcceptSuggestion={onAccept}
        />
      )
      fireEvent.click(screen.getByRole('button', { name: /edit and incorporate suggestion/i }))
      fireEvent.click(screen.getByRole('button', { name: /cancel incorporate/i }))
      expect(onAccept).not.toHaveBeenCalled()
      expect(screen.queryByRole('textbox', { name: /edit to incorporate/i })).not.toBeInTheDocument()
    })
  })
})
