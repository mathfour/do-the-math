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
    return (
      <div className="msg-error" role="alert">
        <span className="msg-tag">Can’t graph that</span>
        <p>{message}</p>
      </div>
    )
  }

  return <p>{envelope.explanation}</p>
}
