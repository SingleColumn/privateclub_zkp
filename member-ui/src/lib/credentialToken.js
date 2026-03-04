/**
 * Mock credential token encoding/decoding.
 * In production this would be an opaque ZKP proof; here we use base64url(JSON) so the
 * verifier can display tier and issued_at when the member shares a link.
 */

const TOKEN_VERSION = 'v1'
const PREFIX = 'pc_v1_'

function base64UrlEncode(str) {
  const base64 = btoa(unescape(encodeURIComponent(str)))
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function base64UrlDecode(str) {
  let base64 = str.replace(/-/g, '+').replace(/_/g, '/')
  const pad = base64.length % 4
  if (pad) base64 += '='.repeat(4 - pad)
  try {
    return decodeURIComponent(escape(atob(base64)))
  } catch {
    return null
  }
}

/**
 * Encode a proof package into a shareable token.
 * @param {{ tier_id: string, issued_at: string, integrity: { status: string } }} credentialPayload
 * @returns {string} token
 */
export function encodeCredentialToken(credentialPayload) {
  const package_ = {
    token_version: TOKEN_VERSION,
    credential_payload: credentialPayload,
  }
  const json = JSON.stringify(package_)
  return PREFIX + base64UrlEncode(json)
}

/**
 * Decode a token into a proof package, or null if invalid.
 * Accepts both new format (pc_v1_<base64json>) and legacy pc_v1_<uuid> (returns mock payload).
 * @param {string} token
 * @returns {{ credential_payload: { tier_id: string, issued_at: string, integrity: { status: string } } } | null}
 */
export function decodeCredentialToken(token) {
  if (!token || typeof token !== 'string') return null
  const trimmed = token.trim()
  if (!trimmed.startsWith(PREFIX)) return null
  const payload = trimmed.slice(PREFIX.length)
  const decoded = base64UrlDecode(payload)
  if (!decoded) {
    return null
  }
  try {
    const pkg = JSON.parse(decoded)
    if (pkg?.token_version === TOKEN_VERSION && pkg?.credential_payload) {
      return pkg
    }
  } catch {
    // legacy token (e.g. pc_v1_uuid) — return null so verifier shows invalid
    return null
  }
  return null
}
