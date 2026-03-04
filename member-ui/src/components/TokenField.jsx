export default function TokenField({ token, onCopy }) {
  const display = token ? `${token.slice(0, 12)}…${token.slice(-4)}` : '—'
  return (
    <div className="flex gap-2">
      <code className="flex-1 px-3 py-2 rounded bg-surface-elevated border border-surface-border text-sm text-gray-300 truncate">
        {display}
      </code>
      <button
        type="button"
        onClick={onCopy}
        className="px-3 py-2 rounded border border-surface-border text-sm text-gray-300 hover:bg-surface-elevated hover:border-gray-500 transition-colors shrink-0"
      >
        Copy
      </button>
    </div>
  )
}
