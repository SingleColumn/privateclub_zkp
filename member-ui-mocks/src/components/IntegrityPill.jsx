const statusConfig = {
  OK: { label: 'OK', className: 'bg-accent/20 text-accent border-accent/40' },
  CHECKING: { label: 'Checking…', className: 'bg-gray-700 text-gray-300 border-surface-border' },
  FAIL: { label: 'Failed', className: 'bg-danger/20 text-danger border-danger/40' },
  UNSUPPORTED: { label: 'Unsupported', className: 'bg-warning/20 text-warning border-warning/40' },
}

export default function IntegrityPill({ status = 'CHECKING' }) {
  const config = statusConfig[status] || statusConfig.CHECKING
  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium border ${config.className}`}
    >
      {config.label}
    </span>
  )
}
