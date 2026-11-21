# Canonical Context Serialization

Guard Bands signs a canonical JSON payload. Every field that travels in the
markers is authenticated, so none of them can be tampered with or downgraded
without invalidating the MAC:

```json
{
  "alg": "GBv2-HMAC-SHA256",
  "content": "<exact wrapped content body>",
  "context": { "...": "..." },
  "exp": 1735689600,
  "iat": 1735688700,
  "iss": "<issuer / minting principal>",
  "kid": "<signing key id>",
  "nonce": "<guard-band nonce>",
  "v": "2"
}
```

The `alg` tag provides domain separation and blocks algorithm downgrade; `iat`
and `exp` bind the band's lifetime so freshness is enforced from authenticated
data (fail closed) rather than from an external ledger alone. Bands signed
with an Ed25519 key carry `"alg": "GBv2-Ed25519"`; the tag follows the
resolved key's type, so a band can never verify under a different algorithm
than the one it was signed with.

Protocol v2 (core `guard-bands` v0.11.0 and later) canonicalizes the payload
with the JSON Canonicalization Scheme (JCS) from
[RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html) and signs the UTF-8
bytes. The [TypeScript core](https://github.com/Cryptix-Security/guard-bands-ts)
uses the same serialization, so bands verify across languages. JCS gives:

- UTF-8 encoded JSON
- object keys sorted by UTF-16 code units
- compact separators with no insignificant spaces
- unescaped non-ASCII characters
- ECMAScript number formatting
- no NaN or Infinity values, duplicate names, or lone surrogates (I-JSON)

Context values must stay inside the I-JSON domain: finite numbers and valid
Unicode strings. The normative description is the core
[wire protocol](https://github.com/Cryptix-Security/guard-bands/blob/main/docs/PROTOCOL.md).

This makes context key order irrelevant:

```json
{"request_id":"req-001","user":"alice"}
```

and:

```json
{"user":"alice","request_id":"req-001"}
```

produce the same authenticated context.

## Context Design

Context should include the values that make a wrapped payload valid for exactly the intended use:

- `request_id` or workflow execution id
- `tenant_id` or account boundary
- authenticated user or service principal
- policy path or tool path
- model/workflow version when relevant
- timestamp or expiration bucket when using time-bounded replay protection

Do not include unstable values that legitimately change between wrap and verify unless they are intentionally part of the security decision.

## Compatibility Note

Changing canonicalization changes MAC input, so the serializer is versioned
protocol behavior. Protocol v1 used Python's `json.dumps(sort_keys=True,
separators=(",", ":"), ensure_ascii=False, allow_nan=False)` with `GBv1-*`
algorithm tags; protocol v2 uses JCS with `GBv2-*` tags. The version and the
algorithm tag are both inside the signed payload, so a band cannot be
relabelled from one version to the other.

The core library still verifies v1 bands during migration but signs v2 by
default. When signers and verifiers are deployed separately (for example the
dual-channel data and control planes), upgrade every verifier first; until
then, signers can be constructed with `GuardBandCrypto(..., signing_version="1")`.
See the core
[rollout steps](https://github.com/Cryptix-Security/guard-bands/blob/main/docs/PROTOCOL.md#v1-to-v2-rollout).

The current marker format includes protocol version `v:2`, issued/expiry
timestamps, and the minting issuer:

```text
⟪INERT:START:v:2:r:nonce:iat:1735688700:exp:1735689600⟫
content
⟪INERT:END:mac:signature:kid:key001:iss:b64url(issuer)⟫
```
