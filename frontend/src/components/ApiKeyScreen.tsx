import { useState } from 'react'
import { setApiKey } from '../lib/storage'

// All planned providers are shown so the model-agnostic direction is visible;
// only Anthropic is selectable in v1. The rest are "Coming soon".
const PROVIDERS = [
  { id: 'anthropic', label: 'Anthropic', available: true },
  { id: 'openai', label: 'OpenAI', available: false },
  { id: 'azure', label: 'Azure OpenAI', available: false },
  { id: 'gemini', label: 'Google Gemini', available: false },
] as const

export function ApiKeyScreen({ onSubmit }: { onSubmit: (key: string) => void }) {
  const [key, setKey] = useState('')
  const [provider, setProvider] = useState('anthropic')

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = key.trim()
    if (!trimmed) return
    setApiKey(trimmed)
    onSubmit(trimmed)
  }

  return (
    <div className="key-screen">
      <h1>Do the Math</h1>
      <p className="tagline">Describe a graph in plain English — we’ll do the rest.</p>

      <form onSubmit={handleSubmit} className="key-form">
        <fieldset className="providers">
          <legend>AI provider</legend>
          {PROVIDERS.map((p) => (
            <label key={p.id} className={p.available ? 'provider' : 'provider disabled'}>
              <input
                type="radio"
                name="provider"
                value={p.id}
                checked={provider === p.id}
                disabled={!p.available}
                onChange={() => setProvider(p.id)}
              />
              <span>{p.label}</span>
              {!p.available && <span className="badge">Coming soon</span>}
            </label>
          ))}
        </fieldset>

        <p className="providers-note">More AI providers are coming in a future version.</p>

        <label className="key-field">
          <span>Anthropic API key</span>
          <input
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="sk-ant-..."
            autoComplete="off"
            aria-label="Anthropic API key"
          />
        </label>

        <button type="submit" disabled={!key.trim()}>
          Start graphing
        </button>
        <p className="key-privacy">
          Your key is stored in this browser and sent only to Anthropic via the local backend.
        </p>
      </form>
    </div>
  )
}
