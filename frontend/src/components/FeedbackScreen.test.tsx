import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { FeedbackScreen } from './FeedbackScreen'

describe('FeedbackScreen', () => {
  it('offers both a GitHub issue and a copyable email', () => {
    render(<FeedbackScreen onBack={vi.fn()} />)
    expect(screen.getByRole('link', { name: /github issue/i })).toHaveAttribute(
      'href',
      expect.stringContaining('/issues/new'),
    )
    expect(screen.getByText('mathfour.com@gmail.com')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^copy$/i })).toBeInTheDocument()
  })

  it('returns via Back', async () => {
    const onBack = vi.fn()
    render(<FeedbackScreen onBack={onBack} />)
    await userEvent.click(screen.getByRole('button', { name: /back/i }))
    expect(onBack).toHaveBeenCalled()
  })
})
