# Changelog

## v0.2.0 - 2026-08-15

- Added a credential-free MCP 2.x reference flow using the core Guard Bands
  `tools/call` client and server integration.
- Demonstrated bidirectional Ed25519 role separation: the trusted host signs
  inputs and the MCP server signs outputs, while each side holds only the
  other's public verification key.
- Added `make mcp-demo`, reference documentation, and an end-to-end regression
  test covering structured output plus the visible model-facing inert boundary.

## v0.1.0 - 2026-08-15

- Split the enterprise-style API and deployment stack into the
  `guard-bands-reference` repository.
- Replaced the local cryptographic implementation and FastAPI middleware with
  a versioned dependency on the standalone `guard-bands` core package.

- Added an adversarial red-team of the two-channel control plane (`scripts/redteam_control_plane.py`, `make redteam-control-plane`): a battery of enforcement-path bypass attempts (forgery, tampering, wrong-keypair signatures, HMAC/Ed25519 algorithm confusion, foreign issuer, wrong-channel/cross-tenant/context-swap, expired bands, homoglyph markers, oversized/malformed input, marker smuggling, and authorization bypass). Exits non-zero on any bypass so it doubles as a regression guard; 0 bypasses at this revision.
- Added an AgentDojo benchmark harness (`integrations/agentdojo/`, `scripts/run_agentdojo_benchmark.py`, `bench` extra): runs Guard Bands as a defense pipeline (cryptographic spotlighting plus an optional provenance gate) against tool-calling agents, with a free scripted-stub validation path, a cost estimate and confirmation before any live run, and unit tests for the defense mechanisms. See `docs/AGENTDOJO_HARNESS.md` for usage and a note on results with current frontier models.
- Added an AgentDojo-style structural workflow evaluation script and documentation for reproducible local boundary tests.
- Made Makefile Python commands configurable with `PYTHON`, defaulting to `python3`.
- Documentation consistency pass: fixed the FastAPI app version (0.6.0 → 0.7.0), refreshed the research paper to the current feature set and made its release references version-agnostic, added `docs/SECRETS.md` to the README docs table, updated the README/QUICKSTART validation lists to the full current suite, and added Python SDK and two-channel deployment sections to QUICKSTART.

## v0.7.0-poc - 2026-07-12

- Added a first-party Python SDK (`guardbands_sdk`) with sync clients for the main Guard Bands API and the two-channel data/control-plane APIs.
- Added typed SDK response models and domain exceptions for verification failures, authorization failures, rate limits, and cost-threshold prompts.
- Added SDK docs, quickstart examples, package build metadata, and SDK test coverage.

## v0.6.0-poc - 2026-07-11

- Added Ed25519 signing to the core crypto alongside HMAC-SHA256: resolver keys may be raw bytes (HMAC), Ed25519 private keys (sign + verify), or Ed25519 public keys (verification-only). The algorithm tag is derived from the key type and bound into the authenticated payload, so cross-algorithm confusion fails closed. Includes keypair helpers and `make dual-channel-keys`.
- Gave the two-channel planes true cryptographic role separation: the data plane holds the Ed25519 private key, the control plane holds only the public key and cannot forge data-plane provenance. Keys resolve through the pluggable secret provider with **no development fallback** — both services fail closed at startup if key material is missing or malformed.
- Added a two-channel Compose deployment (`deploy/docker-compose.dual-channel.yml`): separate services, separate ports, disjoint networks, split key delivery per container, healthchecks, restart policies, and resource limits. Compose refuses to start without keys.

## v0.5.0-poc - 2026-07-11

- Added a two-channel (data-plane / control-plane) reference architecture (`dual_channel/`): untrusted content and trusted instructions travel through two separate services deployable on different ports, joined at a single cryptographic verification point. The data plane can only wrap content (no tool or instruction surface, marker smuggling rejected at ingest); the control plane admits data only when the MAC-authenticated key id, issuer, and `channel: data` context binding prove it came through the data plane, and takes instructions exclusively from its own authenticated channel. Includes `make dual-channel-demo`, invariant tests, and `docs/DUAL_CHANNEL.md`.

## v0.4.0-poc - 2026-07-04

- Added a pluggable secret provider for secret-bearing settings (`SECRET_KEY`, `GUARD_BAND_KEYS`, API tokens): `SECRETS_BACKEND=env` (default), `aws` (AWS Secrets Manager), or `vault` (HashiCorp Vault KV v2). Cloud SDKs are optional extras (`guard-bands[aws]`, `guard-bands[vault]`).
- Added a hardened production Compose overlay (`deploy/docker-compose.prod.yml`): Caddy TLS front door, no direct port exposure, Keycloak in production mode, restart policies, and CPU/memory limits.
- Hardened the container image: runs as a non-root user (uid 10001) with a `/health` healthcheck and no bytecode/buffering.
- Added `.env.production.example`, `docs/SECRETS.md`, and production-deployment guidance for the hardened stack.
- Bumped version to 0.4.0.

## v0.3.2-poc - 2026-07-04

- Added configurable chat cost guardrails with a `/chat/estimate-cost` preflight endpoint.
- Added threshold-based confirmation for `/chat` requests before calling the model.
- Added actual cost reporting from provider token usage in successful `/chat` responses.
- Added README badges for CI, CodeQL, release, Python version, and license.
- Added a short README evaluation path for first-time visitors.
- Enabled GitHub secret scanning and push protection for the repository.

## v0.3.1-poc - 2026-07-04

- Bumped pinned runtime dependencies for the Python security and maintenance group:
  - `anthropic` from `0.111.0` to `0.112.0`
  - `fastapi` from `0.138.0` to `0.138.1`
- Updated stale test and benchmark Guard Band marker literals to the `v0.3.0` wire format.
- Added a manual `workflow_dispatch` trigger to the CI workflow.

## v0.3.0-poc - 2026-06-28

- Bound all marker metadata into the MAC: a domain-separated algorithm tag (`GBv1-HMAC-SHA256`), protocol version, key id, and issuer are now authenticated, preventing downgrade and metadata tampering. **Breaking:** the wire format changed and v0.2.0 bands no longer verify.
- Added authenticated issued/expiry timestamps (`iat`/`exp`) so bands fail closed when stale, independent of the replay ledger. TTL is configurable via `GUARD_BAND_TTL_SECONDS`.
- Stamped an authenticated issuer into each band; the `/wrap` endpoint records the SSO principal and rejects context that contradicts the authenticated user, closing the open signing-oracle gap.
- Removed the redundant SHA-256 marker hash (`h`); the MAC is the sole integrity guarantee, simplifying the parser and removing an info-leaking error path.
- Added Hypothesis property-based fuzz tests for the hand-rolled parser (no crashes, no false-accepts) plus tests for metadata, issuer, and expiry tampering.
- Removed the stale `Guard-Bands-Paper.pdf` binary snapshot; `Guard-Bands-Paper.md` is now the single source of truth, and all links point to it.

## v0.2.0-poc - 2026-06-27

- Added SQLite-backed persistent replay ledger configuration for single-node pilots.
- Added authorization helper examples for role, tenant, user, and policy-path checks.
- Added a reference support-ticket FastAPI app and `make reference-demo`.
- Added production deployment, authorization, and reference-app documentation.
- Added FastAPI Guard Band verification middleware for protected request-body routes.
- Added an API-key-free FastAPI demo runnable with `make demo`.
- Added parser and verification micro-benchmarks runnable with `make bench`.
- Added architecture/threat-model documentation and operational limits guidance.
- Expanded integration documentation around FastAPI instead of proxy-based integrations.
- Added tests for FastAPI middleware enforcement and unsupported sensitive tool calls.

## v0.1.0-poc

- Converted security checks from a manual script into a pytest suite.
- Added GitHub Actions CI for Python 3.11 and 3.12.
- Pinned Python dependency versions in `requirements.txt`.
- Added canonical JSON serialization for Guard Band MAC payloads.
- Included nonce values in authenticated MAC input.
- Added app-side enforcement that guard-banded chat content must be verified before final model responses are accepted.
- Added API curl examples, key-management expectations, and replay-protection examples.
- Updated vulnerable dependency pins for `cryptography`, `python-dotenv`, `requests`, and `pytest`.
- Added Dependabot configuration for future pip and GitHub Actions maintenance updates.
