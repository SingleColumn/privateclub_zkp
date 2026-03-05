export default function ShareLinkButton({ onCopyLink }) {
  return (
    <button
      type="button"
      onClick={onCopyLink}
      className="w-full py-2.5 px-4 rounded-lg border border-surface-border text-sm text-gray-300 hover:bg-surface-elevated hover:border-gray-500 transition-colors"
    >
      Copy link to share
    </button>
  )
}
