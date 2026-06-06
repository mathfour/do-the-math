// "Send feedback" — opens a pre-filled GitHub issue on the repo. No backend or
// third party needed; the title/body are seeded so reports arrive structured.
const REPO = 'https://github.com/mathfour/do-the-math'
const TITLE = 'Feedback: '
const BODY = `Thanks for trying Do the Math!

**What were you trying to graph?**


**What happened, or what would you like to see?**

`

export const FEEDBACK_URL = `${REPO}/issues/new?title=${encodeURIComponent(
  TITLE,
)}&body=${encodeURIComponent(BODY)}`

export function FeedbackLink({ className = '' }: { className?: string }) {
  return (
    <a className={className} href={FEEDBACK_URL} target="_blank" rel="noreferrer">
      Send feedback
    </a>
  )
}
