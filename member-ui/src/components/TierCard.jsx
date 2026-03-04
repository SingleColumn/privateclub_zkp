export default function TierCard({ tier, selected, onSelect }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(tier.id)}
      className={`
        w-full text-left px-4 py-3 rounded-lg border transition-all
        ${selected
          ? 'bg-surface-elevated border-accent ring-1 ring-accent/30'
          : 'bg-surface-elevated border-surface-border hover:border-gray-500'
        }
      `}
    >
      <div className="flex items-center justify-between">
        <span className="font-medium text-white">{tier.label}</span>
        {selected && (
          <span className="text-accent" aria-hidden="true">✓</span>
        )}
      </div>
    </button>
  )
}
