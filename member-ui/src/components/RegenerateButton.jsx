export default function RegenerateButton({ onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
    >
      Regenerate
    </button>
  )
}
