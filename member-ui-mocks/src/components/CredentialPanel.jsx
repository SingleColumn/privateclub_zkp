import CredentialSummary from './CredentialSummary.jsx'
import QrCard from './QrCard.jsx'
import TokenField from './TokenField.jsx'
import ShareLinkButton from './ShareLinkButton.jsx'
import RegenerateButton from './RegenerateButton.jsx'

function formatIssuedAtTimestamp(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  const day = d.getUTCDate()
  const month = d.toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' })
  const year = d.getUTCFullYear()
  const h = String(d.getUTCHours()).padStart(2, '0')
  const m = String(d.getUTCMinutes()).padStart(2, '0')
  const s = String(d.getUTCSeconds()).padStart(2, '0')
  return `${day} ${month} ${year}, ${h}:${m}:${s} UTC`
}

export default function CredentialPanel({
  tierLabel,
  issuedAt,
  token,
  shareLink,
  onCopyToken,
  onCopyLink,
  onRegenerate,
}) {
  const issuedAtLabel = formatIssuedAtTimestamp(issuedAt)
  return (
    <div className="mt-10 p-6 rounded-xl bg-surface-elevated border border-surface-border space-y-6">
      <h2 className="text-sm font-medium text-gray-400">Your proof credential</h2>
      <CredentialSummary tierLabel={tierLabel} issuedAtLabel={issuedAtLabel} />
      <p className="text-xs text-gray-500">
        Share the link in a message so the verifier can open it in one tap. No copy-paste needed.
      </p>
      <div className="flex flex-col sm:flex-row gap-6 items-start">
        <QrCard value={token || shareLink} />
        <div className="flex-1 w-full space-y-3 min-w-0">
          <ShareLinkButton onCopyLink={onCopyLink} />
          {shareLink && (
            <a
              href={shareLink}
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full py-2.5 px-4 rounded-lg border border-surface-border text-sm text-gray-400 hover:bg-surface-elevated hover:border-gray-500 hover:text-gray-300 transition-colors text-center"
            >
              Preview as verifier
            </a>
          )}
          <div>
            <span className="block text-xs text-gray-500 mb-1.5">Token (fallback)</span>
            <TokenField token={token} onCopy={() => onCopyToken?.()} />
          </div>
          <RegenerateButton onClick={onRegenerate} />
        </div>
      </div>
    </div>
  )
}
