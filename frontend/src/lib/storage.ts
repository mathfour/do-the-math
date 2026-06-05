// The Anthropic API key lives only in the browser's localStorage and is sent
// only to our backend (which forwards it only to Anthropic). It is never sent
// anywhere else.

const KEY = 'do-the-math:anthropic-key'
const LLM_SUMMARIES = 'do-the-math:llm-summaries'

export function getApiKey(): string | null {
  return localStorage.getItem(KEY)
}

export function setApiKey(key: string): void {
  localStorage.setItem(KEY, key)
}

export function clearApiKey(): void {
  localStorage.removeItem(KEY)
}

// Whether the user opted into AI-written result lines (default off).
export function getLlmSummaries(): boolean {
  return localStorage.getItem(LLM_SUMMARIES) === '1'
}

export function setLlmSummaries(on: boolean): void {
  localStorage.setItem(LLM_SUMMARIES, on ? '1' : '0')
}
