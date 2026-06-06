import { useEffect, useRef, useState } from 'react'
import { postChat } from '../lib/api'
import { getLlmSummaries } from '../lib/storage'
import type { ChatTurn, Envelope } from '../types'
import { AssistantMessage } from './AssistantMessage'

type ChatMessage =
  | { id: number; role: 'user'; text: string }
  | { id: number; role: 'assistant'; envelope: Envelope }

// Text form of an assistant turn, used as conversation history so the model can
// complete a clarification ("the vertex is (1,2)") against the prior question.
function envelopeToText(envelope: Envelope): string {
  if (envelope.type === 'clarification') return String(envelope.payload.question ?? '')
  return envelope.explanation
}

function toHistory(messages: ChatMessage[]): ChatTurn[] {
  return messages.map((m) =>
    m.role === 'user'
      ? { role: 'user', content: m.text }
      : { role: 'assistant', content: envelopeToText(m.envelope) },
  )
}

export function Chat({ apiKey }: { apiKey: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const nextId = useRef(0)
  // Id of the newest user message — scrolled to the top of the view so the new
  // prompt and its result come into view (it stays pinned as the result loads).
  const scrollTargetId = useRef<number | null>(null)

  useEffect(() => {
    if (scrollTargetId.current == null) return
    const el = document.querySelector<HTMLElement>(`[data-msg-id="${scrollTargetId.current}"]`)
    el?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
  }, [messages, loading])

  async function send(event?: React.FormEvent) {
    event?.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    const history = toHistory(messages)
    const userId = nextId.current++
    scrollTargetId.current = userId
    setMessages((prev) => [...prev, { id: userId, role: 'user', text }])
    setInput('')
    setLoading(true)
    try {
      const envelope = await postChat(text, history, apiKey, getLlmSummaries())
      setMessages((prev) => [...prev, { id: nextId.current++, role: 'assistant', envelope }])
    } finally {
      // postChat is contractually non-throwing, but guard so a future change
      // can never strand the UI in the loading state.
      setLoading(false)
    }
  }

  return (
    <div className="chat">
      {/* A live region so new graph/clarification/error results are announced. */}
      <div className="messages" role="log" aria-live="polite">
        {messages.length === 0 && (
          <div className="empty-hint">
            <p>What would you like me to graph?</p>
            <p>You can use regular words like:</p>
            <ul>
              <li>A line through (-2, 8) and (42, 0)</li>
              <li>Please give me a parabola with vertex (1, 2) opening upward</li>
              <li>The plain old tangent graph</li>
            </ul>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} data-msg-id={m.id} className={`message ${m.role}`}>
            {m.role === 'user' ? <p>{m.text}</p> : <AssistantMessage envelope={m.envelope} />}
          </div>
        ))}
        {loading && <p className="thinking">Working it out…</p>}
      </div>

      <form className="composer" onSubmit={send}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            // Enter sends; Shift+Enter inserts a new line (like Claude / ChatGPT).
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void send()
            }
          }}
          rows={3}
          placeholder="Describe a graph…  (Enter to send, Shift+Enter for a new line)"
          aria-label="Describe a graph"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}
