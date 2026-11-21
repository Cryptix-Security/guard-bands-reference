# Architecture and Threat Model

The Guard Bands mechanism is documented in the core library repository. This repository pins core `v0.10.0` (see `pyproject.toml`), so the links below point at the core docs for that tag. Update them when the pin moves.

- [Core architecture and threat model](https://github.com/Cryptix-Security/guard-bands/blob/v0.10.0/docs/ARCHITECTURE.md): trust boundaries, signing and verification flow, marker format, FastAPI middleware, MCP integration, threats addressed, and what is out of scope.
- [Core research document](https://github.com/Cryptix-Security/guard-bands/blob/v0.10.0/docs/RESEARCH.md): design rationale, security claims, and assumptions.

## What this repository adds

The core library provides signing, verification, canonical serialization, replay primitives, and the FastAPI and MCP integrations. This repository is a reference deployment built on top of it:

| Area | Where |
|---|---|
| Main API (`/wrap`, `/verify`, `/chat`) with SSO, rate limiting, and audit sinks | `app/`, [`API_EXAMPLES.md`](API_EXAMPLES.md) |
| Authorization of sensitive tool calls | [`AUTHORIZATION.md`](AUTHORIZATION.md) |
| Separate data and control planes with an Ed25519 join point | [`DUAL_CHANNEL.md`](DUAL_CHANNEL.md) |
| Support-ticket reference workflow | [`REFERENCE_APP.md`](REFERENCE_APP.md) |
| Secret backends (env, AWS Secrets Manager, Vault) | [`SECRETS.md`](SECRETS.md) |
| Deployment checklist | [`PRODUCTION_DEPLOYMENT.md`](PRODUCTION_DEPLOYMENT.md) |
| Deployment architecture and evidence | [`../Guard-Bands-Paper.md`](../Guard-Bands-Paper.md) |

## Production notes for this stack

- Keep signing keys outside source control; load them through a managed backend (see [`SECRETS.md`](SECRETS.md) and [`KEY_MANAGEMENT.md`](KEY_MANAGEMENT.md)).
- Use a shared nonce ledger when the API runs with multiple workers or replicas (see [`REPLAY_PROTECTION.md`](REPLAY_PROTECTION.md)).
- Bind context to tenant, user, request, policy path, and downstream tool path. The `/wrap` endpoint rejects a context `user` that contradicts the SSO principal.
- Terminate TLS at a production-grade proxy or platform edge.
- Keep audit logs immutable enough for investigation and retention needs.
