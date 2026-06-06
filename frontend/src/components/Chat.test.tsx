import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Envelope } from '../types'

// GraphView pulls in plotly.js-dist-min (a heavy browser bundle); stub it.
vi.mock('plotly.js-dist-min', () => ({ default: { react: vi.fn(), purge: vi.fn() } }))
vi.mock('../lib/api', () => ({ postChat: vi.fn() }))

import { postChat } from '../lib/api'
import { Chat } from './Chat'

const mockPostChat = vi.mocked(postChat)

const graphEnvelope: Envelope = {
  type: 'graph',
  explanation: 'Interpreted your request and derived y = (x - 1)**2 + 2.',
  payload: {
    figure: { data: [], layout: { title: { text: 'y = (x − 1)² + 2' } } },
    equation: 'y = (x - 1)**2 + 2',
    ir: { kind: 'parabola_vertex_direction', vertex: [1, 2], direction: 'up' },
  },
}

beforeEach(() => mockPostChat.mockReset())

async function sendMessage(text: string) {
  await userEvent.type(screen.getByLabelText(/describe a graph/i), text)
  await userEvent.click(screen.getByRole('button', { name: /send/i }))
}

describe('Chat', () => {
  it('marks the messages list as a polite live region', () => {
    render(<Chat apiKey="sk-test" />)
    expect(screen.getByRole('log')).toHaveAttribute('aria-live', 'polite')
  })

  it('renders the user turn and a graph response with reasoning', async () => {
    mockPostChat.mockResolvedValue(graphEnvelope)
    render(<Chat apiKey="sk-test" />)

    await sendMessage('a parabola with vertex (1,2) up')

    expect(screen.getByText('a parabola with vertex (1,2) up')).toBeInTheDocument()
    // The graph announces the actual equation to screen readers.
    expect(
      await screen.findByRole('img', { name: /graph of y = \(x − 1\)² \+ 2/i }),
    ).toBeInTheDocument()
    // Reasoning panel surfaces the derived equation and the IR.
    expect(screen.getByText('y = (x - 1)**2 + 2')).toBeInTheDocument()
    expect(screen.getByText(/parabola_vertex_direction/)).toBeInTheDocument()
  })

  it('renders a clarification question', async () => {
    mockPostChat.mockResolvedValue({
      type: 'clarification',
      explanation: 'Where is the vertex?',
      payload: { question: 'Where is the vertex of the parabola?', field: 'vertex' },
    })
    render(<Chat apiKey="sk-test" />)

    await sendMessage('graph a parabola')
    expect(await screen.findByText(/where is the vertex of the parabola/i)).toBeInTheDocument()
  })

  it('renders an out-of-scope reason gently, with what it can graph', async () => {
    mockPostChat.mockResolvedValue({
      type: 'error',
      explanation: 'not supported',
      payload: { message: "Implicit equations aren't supported in v1.", reason: 'implicit' },
    })
    render(<Chat apiKey="sk-test" />)

    await sendMessage('graph x^2 + y^2 = 25')
    expect(await screen.findByText(/i can only graph functions/i)).toBeInTheDocument()
    expect(screen.getByText(/implicit equations aren't supported/i)).toBeInTheDocument()
    // The capabilities note (what it CAN do) is shown.
    expect(screen.getByText(/single-variable function/i)).toBeInTheDocument()
    expect(screen.getByText('Lines')).toBeInTheDocument()
    // It's informational, not an error alert.
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('answers a help request with the capabilities', async () => {
    mockPostChat.mockResolvedValue({
      type: 'help',
      explanation: "Here's what I can graph right now.",
      payload: {},
    })
    render(<Chat apiKey="sk-test" />)

    await sendMessage('what can I do?')
    expect(await screen.findByText(/here's what i can graph/i)).toBeInTheDocument()
    expect(screen.getByText(/single-variable function/i)).toBeInTheDocument()
    expect(screen.getByText('Lines')).toBeInTheDocument()
    // It's a friendly answer, not an error alert.
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('renders a real failure (bad key) as an alert', async () => {
    mockPostChat.mockResolvedValue({
      type: 'error',
      explanation: 'no key',
      payload: { message: 'No Anthropic API key provided.', reason: 'missing_api_key' },
    })
    render(<Chat apiKey="sk-test" />)

    await sendMessage('a parabola')
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/no anthropic api key/i)
  })

  it('sends prior turns as history on the next message', async () => {
    mockPostChat.mockResolvedValue(graphEnvelope)
    render(<Chat apiKey="sk-test" />)

    await sendMessage('first')
    await sendMessage('second')

    const lastCall = mockPostChat.mock.calls.at(-1)!
    const [message, history, apiKey] = lastCall
    expect(message).toBe('second')
    expect(apiKey).toBe('sk-test')
    expect(history[0]).toEqual({ role: 'user', content: 'first' })
  })
})
