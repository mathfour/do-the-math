import type { Envelope, GraphPayload } from '../types'
import { GraphView } from './GraphView'
import { ReasoningPanel } from './ReasoningPanel'

// Renders one agent envelope uniformly by its `type`. Solution/proof have no
// v1 producer but fall through to the explanation so future agents slot in.
export function AssistantMessage({ envelope }: { envelope: Envelope }) {
  if (envelope.type === 'graph') {
    const payload = envelope.payload as unknown as GraphPayload
    return (
      <div className="msg-graph">
        <p className="explanation">{envelope.explanation}</p>
        <GraphView figure={payload.figure} />
        <ReasoningPanel payload={payload} />
      </div>
    )
  }

  if (envelope.type === 'clarification') {
    const question = String(envelope.payload.question ?? envelope.explanation)
    return (
      <div className="msg-clarify">
        <span className="msg-tag">I need a bit more</span>
        <p>{question}</p>
      </div>
    )
  }

  if (envelope.type === 'error') {
    const message = String(envelope.payload.message ?? envelope.explanation)
    const reason = String(envelope.payload.reason ?? '')

    // "Scope" responses (out-of-scope shapes, or a help question we can't graph)
    // are informational, not failures — show a gentle note + what we *can* do.
    if (SCOPE_REASONS.has(reason)) {
      return (
        <div className="msg-scope">
          <p className="msg-scope-head">Aw, man… I can only graph right now.</p>
          <p>{message}</p>
          <Capabilities />
        </div>
      )
    }

    // Real failures (bad key, server unreachable) stay an alert.
    return (
      <div className="msg-error" role="alert">
        <span className="msg-tag">Hmm, something went wrong</span>
        <p>{message}</p>
      </div>
    )
  }

  return <p>{envelope.explanation}</p>
}

// Reasons that mean "out of scope / I can't graph that yet" rather than a
// genuine failure — these get the friendly capabilities note.
const SCOPE_REASONS = new Set([
  'implicit',
  'parametric',
  'polar',
  'piecewise',
  'inequality',
  'not_a_function',
  'unknown',
  'invalid_intent',
])

function Capabilities() {
  return (
    <div className="capabilities">
      <p>
        Right now I can graph any single-variable function, <em>y = f(x)</em>:
      </p>
      <ul>
        <li>Lines</li>
        <li>Parabolas &amp; other polynomials</li>
        <li>Sine, cosine, tangent</li>
        <li>Exponentials &amp; logarithms</li>
      </ul>
      <p>
        Just describe one in plain English — like “a parabola with vertex (1, 2) opening up” or “the
        line through (0, 0) and (2, 4).”
      </p>
    </div>
  )
}
