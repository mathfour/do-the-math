import type { GraphPayload } from '../types'

// Surfaces the two reasoning steps the demo narrative depends on: the Math
// Intent (IR) the LLM produced, and the equation SymPy derived from it.
export function ReasoningPanel({ payload }: { payload: GraphPayload }) {
  return (
    <details className="reasoning">
      <summary>How this was derived</summary>
      <div className="reasoning-step">
        <span className="reasoning-label">1. Math Intent (from your words)</span>
        <pre className="reasoning-ir">{JSON.stringify(payload.ir, null, 2)}</pre>
      </div>
      <div className="reasoning-step">
        <span className="reasoning-label">2. Equation (derived by SymPy)</span>
        <code className="reasoning-equation">{payload.equation}</code>
      </div>
    </details>
  )
}
