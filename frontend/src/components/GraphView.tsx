import { useEffect, useRef } from 'react'
import Plotly from 'plotly.js-dist-min'
import type { PlotlyFigure } from '../types'

// Renders a Plotly figure spec from the backend into an interactive plot.
export function GraphView({ figure }: { figure: PlotlyFigure }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    Plotly.react(el, figure.data, figure.layout, {
      responsive: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['lasso2d', 'select2d'],
    })
    return () => Plotly.purge(el)
  }, [figure])

  // Announce the actual equation to screen readers, not a generic "graph".
  const title = (figure.layout.title as { text?: string } | undefined)?.text
  return (
    <div
      className="graph"
      ref={ref}
      role="img"
      aria-label={title ? `Graph of ${title}` : 'Graph'}
    />
  )
}
