import { useState } from 'react'
import './App.css'
import { ApiKeyScreen } from './components/ApiKeyScreen'
import { Chat } from './components/Chat'
import { clearApiKey, getApiKey } from './lib/storage'

export default function App() {
  const [apiKey, setKey] = useState<string | null>(() => getApiKey())

  if (!apiKey) {
    return <ApiKeyScreen onSubmit={setKey} />
  }

  function startOver() {
    clearApiKey()
    setKey(null)
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <h1>Do the Math</h1>
          <span className="header-by">brought to you by</span>
          <a href="https://mathfour.com" target="_blank" rel="noreferrer" aria-label="MathFour.com">
            <img className="header-logo" src="/mathfour-logo.png" alt="MathFour.com" />
          </a>
        </div>
        <button type="button" className="link-button" onClick={startOver}>
          Start over
        </button>
      </header>
      <Chat apiKey={apiKey} />
    </div>
  )
}
