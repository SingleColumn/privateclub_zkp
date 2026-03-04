export default function TimestampLabel({ label, value }) {
  return (
    <div>
      <span className="block text-xs text-gray-500 mb-0.5">{label}</span>
      <span className="text-sm text-gray-300">{value}</span>
    </div>
  )
}
