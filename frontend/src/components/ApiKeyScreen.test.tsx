import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiKeyScreen } from './ApiKeyScreen'
import { getApiKey } from '../lib/storage'

afterEach(() => localStorage.removeItem('do-the-math:anthropic-key'))

describe('ApiKeyScreen', () => {
  it('lists all planned providers with only Anthropic selectable', () => {
    render(<ApiKeyScreen onSubmit={vi.fn()} />)

    // Order matches the PROVIDERS list: Anthropic (active), then three disabled.
    const [anthropic, ...rest] = screen.getAllByRole('radio')
    expect(anthropic).toBeEnabled()
    expect(anthropic).toBeChecked()
    for (const radio of rest) {
      expect(radio).toBeDisabled()
    }
    // Three "Coming soon" badges, and the future-providers note.
    expect(screen.getAllByText(/coming soon/i)).toHaveLength(3)
    expect(screen.getByText(/more ai providers are coming/i)).toBeInTheDocument()
  })

  it('captures the key, stores it locally, and reports it up', async () => {
    const onSubmit = vi.fn()
    render(<ApiKeyScreen onSubmit={onSubmit} />)

    await userEvent.type(screen.getByLabelText(/anthropic api key/i), 'sk-ant-xyz')
    await userEvent.click(screen.getByRole('button', { name: /start graphing/i }))

    expect(onSubmit).toHaveBeenCalledWith('sk-ant-xyz')
    expect(getApiKey()).toBe('sk-ant-xyz') // persisted to localStorage, nowhere else
  })

  it('disables submit until a key is entered', () => {
    render(<ApiKeyScreen onSubmit={vi.fn()} />)
    expect(screen.getByRole('button', { name: /start graphing/i })).toBeDisabled()
  })
})
