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

  return <div className="graph" ref={ref} role="img" aria-label="graph" />
}
