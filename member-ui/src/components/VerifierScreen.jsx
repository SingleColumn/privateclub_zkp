import { useState, useEffect, useRef } from 'react'
import { TIERS } from '../lib/tiers.js'
import { decodeCredentialToken } from '../lib/credentialToken.js'
import Header from './Header.jsx'
import IntegrityPill from './IntegrityPill.jsx'
import ErrorBanner from './ErrorBanner.jsx'

const WAITING = 'waiting'
const VERIFYING = 'verifying'
const PASS = 'pass'
const FAIL = 'fail'
const DEGRADED = 'degraded'

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

function formatIssuedAtAge(iso) {
  if (!iso) return ''
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

function getTokenFromUrl() {
  if (typeof window === 'undefined') return null
  const params = new URLSearchParams(window.location.search)
  return params.get('t')
}

export default function VerifierScreen() {
  const urlToken = getTokenFromUrl()
  const [tokenInput, setTokenInput] = useState(urlToken ?? '')
  const [status, setStatus] = useState(urlToken ? VERIFYING : WAITING)
  const [result, setResult] = useState(null)
  const [failReason, setFailReason] = useState(null)
  const hasAutoVerified = useRef(false)
  const openedFromLink = useRef(!!urlToken)

  useEffect(() => {
    if (urlToken) setTokenInput(urlToken)
  }, [urlToken])

  function runVerify(token) {
    if (!token || !token.trim()) return
    setFailReason(null)
    setResult(null)
    setStatus(VERIFYING)
    setTimeout(() => {
      const pkg = decodeCredentialToken(token.trim())
      if (!pkg) {
        setStatus(FAIL)
        setFailReason('Invalid or malformed credential token.')
        return
      }
      const payload = pkg.credential_payload
      const integrityStatus = payload?.integrity?.status ?? 'UNSUPPORTED'
      if (integrityStatus === 'FAIL') {
        setStatus(FAIL)
        setFailReason('Device integrity check failed.')
        return
      }
      if (integrityStatus === 'UNSUPPORTED') {
        setStatus(DEGRADED)
        setResult({
          tierLabel: TIERS.find((t) => t.id === payload?.tier_id)?.label ?? '—',
          issuedAt: payload?.issued_at,
          integrityStatus: 'UNSUPPORTED',
        })
        return
      }
      setStatus(PASS)
      setResult({
        tierLabel: TIERS.find((t) => t.id === payload?.tier_id)?.label ?? '—',
        issuedAt: payload?.issued_at,
        integrityStatus: 'OK',
      })
    }, 1200)
  }

  useEffect(() => {
    if (urlToken && !hasAutoVerified.current) {
      hasAutoVerified.current = true
      runVerify(urlToken)
    }
  }, [urlToken])

  const handleVerify = () => runVerify(tokenInput)

  const isLinkFlow = !!urlToken
  const headerSubtitle = isLinkFlow
    ? (status === VERIFYING ? 'Verifying the credential you opened.' : null)
    : 'Open a shared credential link to verify, or paste a token below.'

  return (
    <div className="min-h-screen bg-surface text-gray-100">
      <div className="max-w-lg mx-auto px-5 py-10">
        <Header
          title="Verify Received Credential"
          subtitle={headerSubtitle}
        />

        {status === VERIFYING && urlToken && (
          <div className="py-8 flex flex-col items-center justify-center gap-4">
            <span className="inline-block w-8 h-8 border-2 border-surface border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-400 text-sm">Verifying credential…</p>
          </div>
        )}

        {(status === WAITING || (status === VERIFYING && !urlToken)) && (
          <div className="space-y-4">
            <label className="block text-sm font-medium text-gray-400">
              Credential link or token
            </label>
            <textarea
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="Paste token or open a link with ?t=..."
              rows={3}
              className="w-full px-4 py-3 rounded-lg bg-surface-elevated border border-surface-border text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent resize-none"
              disabled={status === VERIFYING}
            />
            <button
              type="button"
              onClick={handleVerify}
              disabled={status === VERIFYING || !tokenInput.trim()}
              className="w-full py-3 px-4 rounded-lg font-medium bg-accent text-surface border-0 hover:bg-accent-muted focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-surface disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {status === VERIFYING ? (
                <span className="inline-flex items-center gap-2">
                  <span className="inline-block w-4 h-4 border-2 border-surface border-t-transparent rounded-full animate-spin" />
                  Verifying…
                </span>
              ) : (
                'Verify credential'
              )}
            </button>
          </div>
        )}

        {status === FAIL && (
          <>
            <ErrorBanner message={failReason} variant="error" />
            <button
              type="button"
              onClick={() => { setStatus(WAITING); setFailReason(null); }}
              className="mt-4 text-sm text-gray-400 hover:text-gray-300"
            >
              Try another token
            </button>
          </>
        )}

        {(status === PASS || status === DEGRADED) && result && (
          <div className="space-y-6">
            {openedFromLink.current && (
              <p className="text-xs text-gray-500">Opened from shared link.</p>
            )}
            {status === DEGRADED && (
              <ErrorBanner
                message="Integrity attestation is unsupported for this credential. You may still accept it depending on your policy."
                variant="degraded"
              />
            )}
            <div className="p-6 rounded-xl bg-surface-elevated border border-surface-border space-y-4">
              <div className="flex items-center gap-2">
                <span className="text-lg font-medium text-accent">PASS</span>
                {status === DEGRADED && (
                  <span className="text-xs text-warning">(degraded)</span>
                )}
              </div>
              <dl className="grid gap-3 text-sm">
                <div>
                  <dt className="text-gray-500">Tier proven</dt>
                  <dd className="font-medium text-white mt-0.5">{result.tierLabel}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Issued at</dt>
                  <dd className="text-gray-300 mt-0.5">
                    {formatIssuedAtTimestamp(result.issuedAt)}
                    {formatIssuedAtAge(result.issuedAt) && (
                      <span className="text-gray-500 font-normal"> ({formatIssuedAtAge(result.issuedAt)})</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Integrity status</dt>
                  <dd className="mt-1">
                    <IntegrityPill status={result.integrityStatus} />
                  </dd>
                </div>
              </dl>
              <p className="text-xs text-gray-500 pt-2 border-t border-surface-border">
                Decide if this is recent enough for your needs.
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                setStatus(WAITING)
                setResult(null)
                setTokenInput(urlToken ?? '')
                openedFromLink.current = false
              }}
              className="text-sm text-gray-400 hover:text-gray-300"
            >
              Verify another credential
            </button>
          </div>
        )}

        <p className="mt-10 text-center">
          <a href="/" className="text-sm text-gray-500 hover:text-gray-300">
            Generate a credential
          </a>
        </p>
      </div>
    </div>
  )
}
