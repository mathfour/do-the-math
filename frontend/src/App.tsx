import { useEffect, useRef, useState } from 'react'
import './App.css'
import { ApiKeyScreen } from './components/ApiKeyScreen'
import { Chat } from './components/Chat'
import { FeedbackScreen } from './components/FeedbackScreen'
import { clearApiKey, getApiKey, getLlmSummaries, setLlmSummaries } from './lib/storage'

const REPLY_TOOLTIP =
  'The AI always reads your request, and every graph is computed exactly by a math ' +
  'engine — never by the AI. This only changes how the reply sentence is worded: ' +
  '“AI-written” phrases it freshly each time (and uses more API tokens); ' +
  '“Standard” uses a clear written line.'

export default function App() {
  const [apiKey, setKey] = useState<string | null>(() => getApiKey())
  const [aiResponses, setAiResponses] = useState(() => getLlmSummaries())
  const [infoOpen, setInfoOpen] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const infoRef = useRef<HTMLSpanElement>(null)
  const feedbackTriggerRef = useRef<HTMLButtonElement>(null)
  const keyFeedbackTriggerRef = useRef<HTMLButtonElement>(null)
  const wasFeedbackOpen = useRef(false)

  // Return focus to the "Send feedback" trigger when the feedback view closes.
  // Only one of the two screens (chat header / key screen) is mounted at a time,
  // so whichever ref is populated is the trigger that opened the overlay.
  useEffect(() => {
    if (wasFeedbackOpen.current && !showFeedback) {
      ;(feedbackTriggerRef.current ?? keyFeedbackTriggerRef.current)?.focus()
    }
    wasFeedbackOpen.current = showFeedback
  }, [showFeedback])

  // Close the info popover on an outside click or Escape.
  useEffect(() => {
    if (!infoOpen) return
    function onPointerDown(event: MouseEvent) {
      if (infoRef.current && !infoRef.current.contains(event.target as Node)) setInfoOpen(false)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setInfoOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [infoOpen])

  // Reachable from both the key screen and the chat; close returns focus to
  // whichever "Send feedback" trigger opened it (see the focus-return effect).
  if (showFeedback) {
    return <FeedbackScreen onBack={() => setShowFeedback(false)} />
  }

  if (!apiKey) {
    // Pull the AI-responses choice forward when entering the chat.
    return (
      <ApiKeyScreen
        onSubmit={(k) => {
          setAiResponses(getLlmSummaries())
          setKey(k)
        }}
        onFeedback={() => setShowFeedback(true)}
        feedbackButtonRef={keyFeedbackTriggerRef}
      />
    )
  }

  function logOut() {
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
            Replies: <strong>{aiResponses ? 'AI-written' : 'Standard'}</strong>
            <span className="info-wrap" ref={infoRef}>
              <button
                type="button"
                className="info-icon"
                aria-label="What does this mean?"
                aria-expanded={infoOpen}
                aria-describedby={infoOpen ? 'reply-info' : undefined}
                onClick={() => setInfoOpen((open) => !open)}
              >
                ⓘ
              </button>
              {infoOpen && (
                <span className="info-popover" role="tooltip" id="reply-info">
                  {REPLY_TOOLTIP}
                </span>
              )}
            </span>
            <button type="button" className="link-button" onClick={toggleAi}>
              {aiResponses ? 'Use standard' : 'Use AI-written'}
            </button>
          </span>
          <div className="header-actions">
            <button
              ref={feedbackTriggerRef}
              type="button"
              className="link-button"
              onClick={() => setShowFeedback(true)}
            >
              Send feedback
            </button>
            <button type="button" className="link-button" onClick={logOut}>
              Log out
            </button>
          </div>
        </div>
      </header>
      <Chat apiKey={apiKey} />
    </div>
  )
}
