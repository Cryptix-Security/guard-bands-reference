# Guard Bands Reference Deployment: Architecture and Evidence

The canonical Guard Bands research and design document now lives with the core
mechanism:

**[Out-of-Band Guard Bands for LLM Security](https://github.com/Cryptix-Security/guard-bands/blob/main/docs/RESEARCH.md)**

That document defines the security objective, protocol model, trust
assumptions, claims, limitations, FastAPI boundary, and MCP `tools/call`
boundary. Keeping the mechanism and its research narrative together prevents
the specification from drifting across repositories.

This document describes only what the reference deployment adds and what its
evaluation can demonstrate.

## Repository Role

The reference repository consumes
[`guard-bands`](https://github.com/Cryptix-Security/guard-bands) as a versioned
dependency. It does not maintain a second copy of the cryptographic boundary,
parser, replay primitives, FastAPI middleware, or MCP adapter.

It demonstrates how those reusable components fit into a broader application:

- wrap, verify, and chat API surfaces
- a support-ticket workflow with explicit authorization
- dual data-plane and control-plane services
- Ed25519 signing/verification role separation
- an MCP client/server example with separate keys in each direction
- SSO-aware identity propagation
- rate limiting and preflight LLM cost controls
- structured audit events with optional PostgreSQL and Splunk sinks
- environment, AWS Secrets Manager, and HashiCorp Vault secret providers
- Docker Compose and hardened deployment overlays
- Python SDK and integration examples
- an AgentDojo-oriented structural evaluation harness

These components are examples, not requirements of the Guard Bands protocol.
An application can use the core library without adopting this stack.

## Deployment Architecture

The reference stack demonstrates two related patterns.

### In-process application boundary

The API service uses the core library to wrap untrusted input, verify it under
application-derived context, and reject protected flows that skip or fail
verification. Authorization remains a separate gate for sensitive actions.

See:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/AUTHORIZATION.md`](docs/AUTHORIZATION.md)
- [`docs/REFERENCE_APP.md`](docs/REFERENCE_APP.md)

### Dual-channel boundary

The stronger reference topology separates untrusted ingestion from trusted
instruction and execution services:

```text
untrusted content                     trusted instruction / execution
      |                                           |
      v                                           v
+------------------+                   +----------------------+
|    DATA PLANE    | -- signed data -->|    CONTROL PLANE     |
| private signer   |                   | public verifier      |
| no model/tools   |                   | authorization + tools|
+------------------+                   +----------------------+
```

The data plane holds an Ed25519 private signing key. The control plane holds
only its public verification key, so it cannot forge data-plane provenance.
The signature is the cryptographic join point; process or network separation
alone would not provide this property if both sides shared an HMAC secret.

See [`docs/DUAL_CHANNEL.md`](docs/DUAL_CHANNEL.md).

### MCP tool boundary

The MCP example signs complete tool arguments before they cross from the host
to the tool server and signs final tool results on the return path. Separate
Ed25519 pairs provide directional provenance, and text returned to the model
retains visible inert markers.

The reusable policy and wire behavior are specified in the
[core MCP documentation](https://github.com/Cryptix-Security/guard-bands/blob/main/docs/MCP.md).
Reference-specific topology and production guidance are in
[`docs/MCP_REFERENCE.md`](docs/MCP_REFERENCE.md).

## What the Reference Evaluation Shows

The repository's automated tests and demos check application-level invariants
that are outside the core cryptographic unit tests, including:

- protected chat flows fail closed when verification is skipped or fails
- application context takes precedence over model-supplied tool arguments
- unsupported tool calls are rejected
- support-ticket actions retain explicit authorization checks
- dual-channel startup fails without required key material
- data signed for one channel or tenant is rejected in another
- a verification-only control plane cannot mint data-plane bands
- audit, cost, secret-provider, SDK, and API wiring behaves as documented
- the MCP reference topology uses separate signing roles in each direction

The AgentDojo harness supports comparative workflow experiments. It should be
used to report the exact suite, model, configuration, and failure policy rather
than to claim universal prompt-injection prevention. See
[`docs/EVALUATION.md`](docs/EVALUATION.md) and
[`docs/AGENTDOJO_HARNESS.md`](docs/AGENTDOJO_HARNESS.md).

## What It Does Not Show

Passing the reference tests does not establish that:

- correctly signed malicious content is semantically safe
- every LLM application will enforce the boundary correctly
- a model cannot be socially engineered by verified data
- application authorization or tool implementations are secure
- signing keys cannot be compromised
- the deployment is production-ready for every threat environment
- Guard Bands eliminates prompt injection

The reference deployment is evidence that the mechanism can be integrated with
ordinary application controls and tested at meaningful boundaries. Security
claims for the mechanism itself remain those in the
[canonical research document](https://github.com/Cryptix-Security/guard-bands/blob/main/docs/RESEARCH.md).

## Operational Documentation

The deployment-specific documentation includes:

- [`QUICKSTART.md`](QUICKSTART.md) for evaluation setup
- [`docs/PRODUCTION_DEPLOYMENT.md`](docs/PRODUCTION_DEPLOYMENT.md) for pilot
  hardening guidance
- [`docs/SECRETS.md`](docs/SECRETS.md) for secret backends
- [`docs/KEY_MANAGEMENT.md`](docs/KEY_MANAGEMENT.md) for deployment key layout
- [`docs/OWASP_LLM_COVERAGE.md`](docs/OWASP_LLM_COVERAGE.md) for control mapping
- [`docs/LIMITS.md`](docs/LIMITS.md) for reference-stack limits

Guard Bands remains an experimental defense-in-depth mechanism. Feedback,
bypass attempts, threat-model review, and reproducible evaluation results are
welcome in either repository according to whether they concern the core
mechanism or this deployment.
