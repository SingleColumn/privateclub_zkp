export default function ErrorBanner({ message, variant = 'error' }) {
  const isDegraded = variant === 'degraded'
  const bg = isDegraded ? 'bg-warning/10 border-warning/40' : 'bg-danger/10 border-danger/40'
  const text = isDegraded ? 'text-warning' : 'text-danger'
  return (
    <div
      role="alert"
      className={`mt-4 p-3 rounded-lg border ${bg} ${text} text-sm`}
    >
      {message}
    </div>
  )
}
