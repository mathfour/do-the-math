import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// App -> Chat -> GraphView imports plotly; stub it for jsdom.
vi.mock('plotly.js-dist-min', () => ({ default: { react: vi.fn(), purge: vi.fn() } }))

import App from './App'

const KEY = 'do-the-math:anthropic-key'
const LLM = 'do-the-math:llm-summaries'
beforeEach(() => {
  localStorage.removeItem(KEY)
  localStorage.removeItem(LLM)
})
afterEach(() => {
  localStorage.removeItem(KEY)
  localStorage.removeItem(LLM)
})

describe('App key gate', () => {
  it('shows the API key screen when no key is stored', () => {
    render(<App />)
    expect(screen.getByLabelText(/anthropic api key/i)).toBeInTheDocument()
  })

  it('shows the chat once a key is stored', () => {
    localStorage.setItem(KEY, 'sk-ant-xyz')
    render(<App />)
    expect(screen.getByLabelText(/describe a graph/i)).toBeInTheDocument()
  })

  it('transitions from key screen to chat on submit, and back on "Start over"', async () => {
    render(<App />)

    await userEvent.type(screen.getByLabelText(/anthropic api key/i), 'sk-ant-xyz')
    await userEvent.click(screen.getByRole('button', { name: /start graphing/i }))
    expect(screen.getByLabelText(/describe a graph/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /start over/i }))
    expect(screen.getByLabelText(/anthropic api key/i)).toBeInTheDocument()
  })

  it('shows the AI-responses status in the header and toggles it', async () => {
    localStorage.setItem(KEY, 'sk-ant-xyz')
    render(<App />)

    expect(screen.getByText(/ai responses:/i)).toHaveTextContent(/off/i)
    await userEvent.click(screen.getByRole('button', { name: /turn on/i }))
    expect(screen.getByText(/ai responses:/i)).toHaveTextContent(/on/i)
    expect(localStorage.getItem(LLM)).toBe('1')
  })
})
