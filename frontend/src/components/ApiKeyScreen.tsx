import { useState } from 'react'
import { getLlmSummaries, setApiKey, setLlmSummaries } from '../lib/storage'
import { BroughtBy } from './BroughtBy'

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
  const [aiResponses, setAiResponses] = useState(() => getLlmSummaries())

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = key.trim()
    if (!trimmed) return
    setApiKey(trimmed)
    setLlmSummaries(aiResponses)
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

        <label className="ai-responses">
          <input
            type="checkbox"
            checked={aiResponses}
            onChange={(e) => setAiResponses(e.target.checked)}
          />
          <span>
            Use <strong>AI-written replies</strong> — let the AI phrase each result in its own
            conversational words (uses more of your API tokens). Either way, the AI reads your
            request and every graph is computed exactly; this only changes the wording. You can
            switch this anytime from the chat.
          </span>
        </label>

        <button type="submit" disabled={!key.trim()}>
          Start graphing
        </button>
        <p className="key-privacy">
          Your key is stored in this browser and sent only to Anthropic via the local backend.
        </p>
      </form>

      <BroughtBy className="key-screen-credit" />
    </div>
  )
}
