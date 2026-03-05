import TierCard from './TierCard.jsx'

export default function TierSelector({ tiers, selectedId, onSelect }) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-400 mb-3">
        Select proof tier
      </label>
      <div className="space-y-2">
        {tiers.map((tier) => (
          <TierCard
            key={tier.id}
            tier={tier}
            selected={tier.id === selectedId}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  )
}
