import { useState, useCallback } from 'react'
import { TIERS } from '../lib/tiers.js'
import { encodeCredentialToken } from '../lib/credentialToken.js'
import Header from './Header.jsx'
import TierSelector from './TierSelector.jsx'
import StatusRow from './StatusRow.jsx'
import PrimaryActionButton from './PrimaryActionButton.jsx'
import PrivacyNote from './PrivacyNote.jsx'
import ErrorBanner from './ErrorBanner.jsx'
import CredentialPanel from './CredentialPanel.jsx'

const INTEGRITY_OK = 'OK'
const IDLE = 'idle'
const GENERATING = 'generating'
const GENERATED = 'generated'
const ERROR = 'error'

function formatIssuedAt(iso) {
  if (!iso) return null
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now - d
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins} min ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${diffDays} days ago`
}

function mockGenerate(selectedTierId, integrityStatus = 'OK') {
  const issuedAt = new Date().toISOString()
  const token = encodeCredentialToken({
    tier_id: selectedTierId,
    issued_at: issuedAt,
    integrity: { status: integrityStatus },
  })
  return { token, issuedAt }
}

export default function MemberGenerateScreen() {
  const [selectedTierId, setSelectedTierId] = useState(TIERS[0].id)
  const [status, setStatus] = useState(IDLE)
  const [integrityStatus] = useState(INTEGRITY_OK)
  const [issuedAt, setIssuedAt] = useState(null)
  const [token, setToken] = useState(null)
  const [errorMessage, setErrorMessage] = useState(null)
  const [errorVariant, setErrorVariant] = useState('error')

  const selectedTier = TIERS.find((t) => t.id === selectedTierId)
  const timestampDisplay = status === GENERATED && issuedAt
    ? formatIssuedAt(issuedAt)
    : status === IDLE || status === GENERATING
      ? 'Will be set when you generate'
      : null

  const handleGenerate = useCallback(() => {
    setErrorMessage(null)
    setStatus(GENERATING)
    setTimeout(() => {
      const { token: newToken, issuedAt: newIssuedAt } = mockGenerate(selectedTierId, integrityStatus)
      setToken(newToken)
      setIssuedAt(newIssuedAt)
      setStatus(GENERATED)
    }, 1500)
  }, [selectedTierId, integrityStatus])

  const handleRegenerate = useCallback(() => {
    setErrorMessage(null)
    setStatus(GENERATING)
    setTimeout(() => {
      const { token: newToken, issuedAt: newIssuedAt } = mockGenerate(selectedTierId, integrityStatus)
      setToken(newToken)
      setIssuedAt(newIssuedAt)
      setStatus(GENERATED)
    }, 1500)
  }, [selectedTierId, integrityStatus])

  const handleCopyToken = useCallback(() => {
    if (token) navigator.clipboard?.writeText(token)
  }, [token])

  const shareLink = token ? `${typeof window !== 'undefined' ? window.location.origin : ''}/v?t=${encodeURIComponent(token)}` : ''
  const handleCopyLink = useCallback(() => {
    if (shareLink) navigator.clipboard?.writeText(shareLink)
  }, [shareLink])

  return (
    <div className="min-h-screen bg-surface text-gray-100">
      <div className="max-w-lg mx-auto px-5 py-10">
        <Header
          title="Generate Credential"
          subtitle="Share a private proof that you have available funds."
          helpLink="#"
        />

        <TierSelector
          tiers={TIERS}
          selectedId={selectedTierId}
          onSelect={setSelectedTierId}
        />

        <StatusRow
          integrityStatus={integrityStatus}
          timestampLabel="Will be set when you generate"
          timestampValue={timestampDisplay}
        />

        <div className="pt-2">
          <PrimaryActionButton
            loading={status === GENERATING}
            onClick={handleGenerate}
            disabled={status === GENERATING}
          >
            Generate credential
          </PrimaryActionButton>
          <PrivacyNote />
        </div>

        {errorMessage && (
          <ErrorBanner message={errorMessage} variant={errorVariant} />
        )}

        {status === GENERATED && (
          <CredentialPanel
            tierLabel={selectedTier?.label ?? '—'}
            issuedAt={issuedAt}
            token={token}
            shareLink={shareLink}
            onCopyToken={handleCopyToken}
            onCopyLink={handleCopyLink}
            onRegenerate={handleRegenerate}
          />
        )}

        <p className="mt-10 text-center">
          <a href="/v" className="text-sm text-gray-500 hover:text-gray-300">
            Verify a credential
          </a>
        </p>
      </div>
    </div>
  )
}
