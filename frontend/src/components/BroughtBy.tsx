// "brought to you by mathfour.com" credit + logo, used on the key screen and
// in the chat header.
export function BroughtBy({ className = '' }: { className?: string }) {
  return (
    <a
      className={`brought-by ${className}`.trim()}
      href="https://mathfour.com"
      target="_blank"
      rel="noreferrer"
    >
      <span className="brought-by-text">Brought to You By</span>
      <img className="brought-by-logo" src="/mathfour-logo.png" alt="MathFour.com" />
    </a>
  )
}
