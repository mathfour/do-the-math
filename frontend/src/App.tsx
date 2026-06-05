import { useState } from 'react'
import './App.css'
import { ApiKeyScreen } from './components/ApiKeyScreen'
import { Chat } from './components/Chat'
import { clearApiKey, getApiKey, getLlmSummaries, setLlmSummaries } from './lib/storage'

export default function App() {
  const [apiKey, setKey] = useState<string | null>(() => getApiKey())
  const [aiResponses, setAiResponses] = useState(() => getLlmSummaries())

  if (!apiKey) {
    // Pull the AI-responses choice forward when entering the chat.
    return (
      <ApiKeyScreen
        onSubmit={(k) => {
          setAiResponses(getLlmSummaries())
          setKey(k)
        }}
      />
    )
  }

  function startOver() {
    clearApiKey()
    setKey(null)
  }

  function toggleAi() {
    const next = !aiResponses
    setLlmSummaries(next)
    setAiResponses(next)
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <h1>Do the Math</h1>
          <span className="header-by">Brought to you by</span>
          <a href="https://mathfour.com" target="_blank" rel="noreferrer" aria-label="MathFour.com">
            <img className="header-logo" src="/mathfour-logo.png" alt="MathFour.com" />
          </a>
        </div>
        <div className="header-controls">
          <span className={`ai-status ${aiResponses ? 'on' : ''}`.trim()}>
            AI responses: <strong>{aiResponses ? 'On' : 'Off'}</strong>
            <button type="button" className="link-button" onClick={toggleAi}>
              {aiResponses ? 'Turn off' : 'Turn on'}
            </button>
          </span>
          <button type="button" className="link-button" onClick={startOver}>
            Start over
          </button>
        </div>
      </header>
      <Chat apiKey={apiKey} />
    </div>
  )
}
