// plotly.js-dist-min ships prebuilt without bundled types. We use a tiny slice
// of its API (Plotly.react / Plotly.purge), so a loose declaration is enough.
declare module 'plotly.js-dist-min' {
  export function react(
    el: HTMLElement,
    data: unknown[],
    layout?: Record<string, unknown>,
    config?: Record<string, unknown>,
  ): Promise<void>
  export function purge(el: HTMLElement): void
  const Plotly: { react: typeof react; purge: typeof purge }
  export default Plotly
}
