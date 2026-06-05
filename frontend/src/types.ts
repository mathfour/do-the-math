// Mirrors the backend output Envelope (see backend/app/do_the_math/ir.py).
// The frontend renders uniformly off `type`; future agent outputs slot in here.

export type EnvelopeType = 'graph' | 'solution' | 'proof' | 'clarification' | 'error'

export interface PlotlyFigure {
  data: unknown[]
  layout: Record<string, unknown>
}

export interface GraphPayload {
  figure: PlotlyFigure
  equation: string
  ir: Record<string, unknown>
}

export interface ClarificationPayload {
  question: string
  field: string
}

export interface ErrorPayload {
  message: string
  reason: string
}

export interface Envelope {
  type: EnvelopeType
  payload: Record<string, unknown>
  explanation: string
}

// A conversation turn sent back as history to complete a clarification.
export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}
