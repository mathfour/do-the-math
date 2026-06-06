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

  it('transitions from key screen to chat on submit, and back on "Log out"', async () => {
    render(<App />)

    await userEvent.type(screen.getByLabelText(/anthropic api key/i), 'sk-ant-xyz')
    await userEvent.click(screen.getByRole('button', { name: /start graphing/i }))
    expect(screen.getByLabelText(/describe a graph/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /log out/i }))
    expect(screen.getByLabelText(/anthropic api key/i)).toBeInTheDocument()
  })

  it('shows the reply-wording status in the header and toggles it', async () => {
    localStorage.setItem(KEY, 'sk-ant-xyz')
    render(<App />)

    expect(screen.getByText(/replies:/i)).toHaveTextContent(/standard/i)
    await userEvent.click(screen.getByRole('button', { name: /use ai-written/i }))
    expect(screen.getByText(/replies:/i)).toHaveTextContent(/ai-written/i)
    expect(localStorage.getItem(LLM)).toBe('1')
  })

  it('opens the reply-wording info popover on click and closes it again', async () => {
    localStorage.setItem(KEY, 'sk-ant-xyz')
    render(<App />)

    const info = screen.getByRole('button', { name: /what does this mean/i })
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()

    await userEvent.click(info)
    expect(screen.getByRole('tooltip')).toHaveTextContent(/computed exactly/i)

    await userEvent.click(info)
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })

  it('opens the branded feedback screen from the header, then returns', async () => {
    localStorage.setItem(KEY, 'sk-ant-xyz')
    render(<App />)

    await userEvent.click(screen.getByRole('button', { name: /send feedback/i }))
    // Focus moves into the new view (its heading).
    expect(screen.getByRole('heading', { name: /do the math/i })).toHaveFocus()
    // Both options are offered on the branded screen.
    expect(screen.getByRole('link', { name: /github issue/i })).toHaveAttribute(
      'href',
      expect.stringContaining('github.com/mathfour/do-the-math/issues/new'),
    )
    expect(screen.getByText('mathfour.com@gmail.com')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /back/i }))
    expect(screen.getByLabelText(/describe a graph/i)).toBeInTheDocument()
    // Focus returns to the trigger.
    expect(screen.getByRole('button', { name: /send feedback/i })).toHaveFocus()
  })
})
