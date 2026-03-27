import { useState } from 'react'
import type { CreateTermPayload } from '../types'

interface AddTermModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (payload: CreateTermPayload) => Promise<void>
  isPending?: boolean
}

interface FormErrors {
  name?: string
  definition?: string
}

export function AddTermModal({ isOpen, onClose, onSubmit, isPending = false }: AddTermModalProps) {
  const [name, setName] = useState('')
  const [definition, setDefinition] = useState('')
  const [fullName, setFullName] = useState('')
  const [category, setCategory] = useState('')
  const [errors, setErrors] = useState<FormErrors>({})

  if (!isOpen) return null

  function validate(): FormErrors {
    const errs: FormErrors = {}
    if (!name.trim()) errs.name = 'Name is required'
    if (!definition.trim()) errs.definition = 'Definition is required'
    return errs
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (isPending) return
    const errs = validate()
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setErrors({})
    try {
      await onSubmit({ name: name.trim(), definition: definition.trim(), full_name: fullName, category })
      setName('')
      setDefinition('')
      setFullName('')
      setCategory('')
    } catch {
      // onSubmit error surfaces via the mutation's error state in the parent
    }
  }

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="add-term-heading" className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h2 id="add-term-heading" className="text-lg font-semibold text-gray-900 mb-4">Add Term</h2>
        <form onSubmit={handleSubmit} noValidate>
          <div className="mb-4">
            <label htmlFor="term-name" className="block text-sm font-medium text-gray-700 mb-1">
              Term Name *
            </label>
            <input
              id="term-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-invalid={!!errors.name}
              aria-describedby={errors.name ? 'term-name-error' : undefined}
            />
            {errors.name && (
              <p id="term-name-error" className="mt-1 text-xs text-red-600">{errors.name}</p>
            )}
          </div>

          <div className="mb-4">
            <label htmlFor="term-definition" className="block text-sm font-medium text-gray-700 mb-1">
              Definition *
            </label>
            <textarea
              id="term-definition"
              value={definition}
              onChange={(e) => setDefinition(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              aria-invalid={!!errors.definition}
              aria-describedby={errors.definition ? 'term-def-error' : undefined}
            />
            {errors.definition && (
              <p id="term-def-error" className="mt-1 text-xs text-red-600">{errors.definition}</p>
            )}
          </div>

          <div className="mb-4">
            <label htmlFor="term-full-name" className="block text-sm font-medium text-gray-700 mb-1">
              Full Name
            </label>
            <input
              id="term-full-name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="mb-6">
            <label htmlFor="term-category" className="block text-sm font-medium text-gray-700 mb-1">
              Category
            </label>
            <input
              id="term-category"
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={() => {
                setName('')
                setDefinition('')
                setFullName('')
                setCategory('')
                setErrors({})
                onClose()
              }}
              className="px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="px-4 py-2 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isPending ? 'Adding...' : 'Add Term'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
