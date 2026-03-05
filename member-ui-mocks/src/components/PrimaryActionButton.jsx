export default function PrimaryActionButton({ loading, onClick, disabled, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled ?? loading}
      className="
        w-full py-3 px-4 rounded-lg font-medium
        bg-accent text-surface border-0
        hover:bg-accent-muted focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-surface
        disabled:opacity-60 disabled:cursor-not-allowed
        transition-colors
      "
    >
      {loading ? (
        <span className="inline-flex items-center gap-2">
          <span className="inline-block w-4 h-4 border-2 border-surface border-t-transparent rounded-full animate-spin" />
          Generating…
        </span>
      ) : (
        children
      )}
    </button>
  )
}
