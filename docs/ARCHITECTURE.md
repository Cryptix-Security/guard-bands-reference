# Architecture and Threat Model

Guard Bands separates untrusted content from trusted instructions by giving the application a cryptographic boundary it can verify before sensitive behavior is allowed.

## Trust Boundaries

| Boundary | Trusted side | Untrusted side |
|---|---|---|
| Wrapping | application signer and key resolver | uploaded files, retrieved documents, tickets, web pages, emails |
| Verification | application verifier and expected context | model-generated tool inputs and user-controlled prompt text |
| Tool execution | application policy and authorization checks | any text inside model context, including verified document text |
| Audit | server-side event logger | user, model, and document content |

The model is not the root of trust. It can request verification, but the application chooses the verification context and decides whether a tool path is allowed.

## Signing Flow

1. Application receives untrusted content.
2. Application builds the expected context, such as request id, tenant id, user id, model, and policy path.
3. `GuardBandCrypto.wrap_content` generates a nonce, stamps issued/expiry timestamps and the minting issuer, and signs the canonical payload.
4. The wrapped block is passed downstream as inert data.

The marker format is versioned, and every field is authenticated by the MAC:

```text
⟪INERT:START:v:1:r:b64url(nonce):iat:issued_at:exp:expires_at⟫
[untrusted content]
⟪INERT:END:mac:b64(mac):kid:keyid:iss:b64url(issuer)⟫
```

## Verification Flow

1. Application detects a complete Guard Band block.
2. Application verifies marker structure, protocol version, nonce, key id, issuer, MAC, lifetime (expiry), and context.
3. Optional replay protection checks the nonce against the canonical context.
4. Application treats verified content as data, not authority.
5. Sensitive tool calls still require normal authorization and policy checks.

Verification fails closed. If a block is malformed, tampered with, signed by an unknown key, bound to the wrong context, expired, or replayed inside the same context, the application rejects it.

## FastAPI Integration

The core package includes `guardbands.integrations.fastapi.GuardBandVerificationMiddleware`
for routes that should only accept verified Guard Band request bodies.

```python
from fastapi import FastAPI, Request

from guardbands import GuardBandCrypto
from guardbands.integrations.fastapi import (
    GuardBandVerificationMiddleware,
    guard_band_verification,
)

app = FastAPI()
crypto = GuardBandCrypto(b"dev-secret")

app.add_middleware(
    GuardBandVerificationMiddleware,
    crypto=crypto,
    required_paths={"/tool-input"},
)

@app.post("/tool-input")
async def tool_input(payload: dict, request: Request):
    verification = guard_band_verification(request)
    return {"verified_content": verification["content"]}
```

This middleware is useful when a route should never process unverified tool input. It verifies before the route handler runs and attaches the verification result to `request.state.guard_band_verification`.

## Threats Addressed

- forged Guard Band markers
- modified wrapped content
- unknown signing keys
- context replay across users, tenants, requests, or policy paths
- incomplete or malformed markers
- model attempts to skip verification
- model attempts to call unsupported tools from guarded content

## Out of Scope

Guard Bands do not prove content is true, safe, benign, or authorized. Verified content can still contain malicious claims, social engineering, or unsafe business requests. Production systems still need least-privilege tools, authorization checks, human approval for high-risk actions, output validation, monitoring, and incident response.

## Production Notes

- Keep signing keys outside source control.
- Use an external key manager or secret manager for production keys.
- Use a shared nonce ledger for multi-process replay protection.
- Bind context to tenant, user, request, policy path, and downstream tool path.
- Terminate TLS at a production-grade proxy or platform edge.
- Keep audit logs immutable enough for investigation and retention needs.
