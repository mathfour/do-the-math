// Where feedback goes: a pre-filled GitHub issue, or a copyable email address.
const REPO = 'https://github.com/mathfour/do-the-math'
const TITLE = 'Feedback: '
const BODY = `Thanks for trying Do the Math!

**What were you trying to graph?**


**What happened, or what would you like to see?**

`

export const FEEDBACK_URL = `${REPO}/issues/new?title=${encodeURIComponent(
  TITLE,
)}&body=${encodeURIComponent(BODY)}`

export const FEEDBACK_EMAIL = 'mathfour.com@gmail.com'
