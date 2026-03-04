export default function CredentialSummary({ tierLabel, issuedAtLabel }) {
  return (
    <div className="flex flex-wrap gap-6 text-sm">
      <div>
        <span className="text-gray-500">Tier proven</span>
        <span className="ml-2 font-medium text-white">{tierLabel}</span>
      </div>
      <div>
        <span className="text-gray-500">Issued at</span>
        <span className="ml-2 text-gray-300">{issuedAtLabel}</span>
      </div>
    </div>
  )
}
