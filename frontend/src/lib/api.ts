import type { ChatTurn, Envelope } from '../types'

// Backend base URL. Overridable via VITE_API_BASE for non-default setups.
const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

/**
 * Send a message to the backend and return the output envelope. The Anthropic
 * key travels in the X-Anthropic-Key header (localhost only). The backend
 * returns 200 envelopes even for app-level errors; a non-200 is a transport or
 * validation failure, which we surface as an error envelope so the UI never
 * has to special-case fetch failures.
 */
export async function postChat(
  message: string,
  history: ChatTurn[],
  apiKey: string,
): Promise<Envelope> {
  let resp: Response
  try {
    resp = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Anthropic-Key': apiKey },
      body: JSON.stringify({ message, history }),
    })
  } catch {
    return {
      type: 'error',
      payload: {
        message: 'Could not reach the server. Is the backend running?',
        reason: 'network',
      },
      explanation: 'Network error.',
    }
  }

  if (!resp.ok) {
    return {
      type: 'error',
      payload: {
        message: `The server rejected the request (${resp.status}).`,
        reason: 'http_error',
      },
      explanation: 'Request failed.',
    }
  }
  return (await resp.json()) as Envelope
}
