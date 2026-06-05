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

  function changeKey() {
    clearApiKey()
    setKey(null)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Do the Math</h1>
        <button type="button" className="link-button" onClick={changeKey}>
          Change key
        </button>
      </header>
      <Chat apiKey={apiKey} />
    </div>
  )
}
