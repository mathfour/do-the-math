import { useEffect, useRef, useState } from 'react'
import { FEEDBACK_EMAIL, FEEDBACK_URL } from '../lib/feedback'
import { BroughtBy } from './BroughtBy'

// A branded feedback page (styled like the first-run splash) offering two ways
// to reach the author: a pre-filled GitHub issue, or a copyable email address.
export function FeedbackScreen({ onBack }: { onBack: () => void }) {
  const [copied, setCopied] = useState(false)
  const headingRef = useRef<HTMLHeadingElement>(null)

  // Move focus into the new view so keyboard/screen-reader users land here.
  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  async function copyEmail() {
    try {
      await navigator.clipboard.writeText(FEEDBACK_EMAIL)
      setCopied(true)
    } catch {
      setCopied(false) // clipboard unavailable — the address is shown to copy by hand
    }
  }

  return (
    <div className="key-screen">
      <h1 ref={headingRef} tabIndex={-1}>
        Do the Math
      </h1>
      <p className="tagline">We’d love your feedback.</p>

      <div className="feedback-card">
        <p>Tell me what worked, what didn’t, or what you’d like to see next — two easy ways:</p>

        <a className="feedback-option" href={FEEDBACK_URL} target="_blank" rel="noreferrer">
          Open a GitHub issue →
        </a>
        <p className="feedback-note">Quick and trackable (needs a free GitHub account).</p>

        <div className="feedback-email">
          <span>Or email me:</span>
          <code>{FEEDBACK_EMAIL}</code>
          <button type="button" className="link-button" onClick={copyEmail}>
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
        <p className="feedback-note">Paste it into your own email and write me directly.</p>
      </div>

      <button type="button" className="link-button feedback-back" onClick={onBack}>
        ← Back
      </button>

      <BroughtBy className="key-screen-credit" />
    </div>
  )
}
