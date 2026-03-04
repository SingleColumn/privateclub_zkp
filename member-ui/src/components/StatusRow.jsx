import IntegrityPill from './IntegrityPill.jsx'
import TimestampLabel from './TimestampLabel.jsx'

export default function StatusRow({ integrityStatus, timestampLabel, timestampValue }) {
  return (
    <div className="flex flex-wrap gap-6 py-4">
      <div>
        <span className="block text-xs text-gray-500 mb-1.5">Device integrity</span>
        <IntegrityPill status={integrityStatus} />
      </div>
      <div>
        <TimestampLabel label="Snapshot timestamp" value={timestampValue || timestampLabel} />
      </div>
    </div>
  )
}
