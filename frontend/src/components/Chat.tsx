import { useRef, useState } from 'react'
import { postChat } from '../lib/api'
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

  async function send(event: React.FormEvent) {
    event.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    const history = toHistory(messages)
    setMessages((prev) => [...prev, { id: nextId.current++, role: 'user', text }])
    setInput('')
    setLoading(true)
    const envelope = await postChat(text, history, apiKey)
    setMessages((prev) => [...prev, { id: nextId.current++, role: 'assistant', envelope }])
    setLoading(false)
  }

  return (
    <div className="chat">
      <div className="messages">
        {messages.length === 0 && (
          <p className="empty-hint">
            Try: “a parabola with vertex (1, 2) opening upward”, or “the line through (0, 0) and (2,
            4)”.
          </p>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`message ${m.role}`}>
            {m.role === 'user' ? <p>{m.text}</p> : <AssistantMessage envelope={m.envelope} />}
          </div>
        ))}
        {loading && <p className="thinking">Working it out…</p>}
      </div>

      <form className="composer" onSubmit={send}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe a graph…"
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
