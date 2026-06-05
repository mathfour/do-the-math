// The Anthropic API key lives only in the browser's localStorage and is sent
// only to our backend (which forwards it only to Anthropic). It is never sent
// anywhere else.

const KEY = 'do-the-math:anthropic-key'

export function getApiKey(): string | null {
  return localStorage.getItem(KEY)
}

export function setApiKey(key: string): void {
  localStorage.setItem(KEY, key)
}

export function clearApiKey(): void {
  localStorage.removeItem(KEY)
}
