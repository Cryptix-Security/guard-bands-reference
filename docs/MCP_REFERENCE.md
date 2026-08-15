# MCP Reference Flow

The reference deployment includes a credential-free MCP 2.x example that
protects both sides of `tools/call`:

```bash
make mcp-demo
```

The example creates two Ed25519 keypairs with deliberately split roles:

| Component | Private key | Public verification key |
|---|---|---|
| trusted MCP host/client | client input signer | MCP server output verifier |
| MCP server | server output signer | trusted client input verifier |

The guarded client signs the complete arguments object with tenant, user,
policy path, server audience, tool name, logical call id, and direction bound
into the authenticated context. The server reconstructs the expected
application context and verifies the signature before
`search_support_tickets` runs.

The sample tool returns a support ticket containing a prompt-injection string.
The server signs the complete structured result and wraps the model-facing text
block in visible Guard Band markers. The client verifies both layers before
returning the result.

The example uses an in-memory MCP transport so it runs without ports or
credentials. The same extension and client wrapper operate over stdio and
Streamable HTTP because enforcement happens at the MCP `tools/call` layer, not
at the HTTP layer.

For production:

- load long-lived directional keys from a secret manager or KMS
- derive the server's context from authenticated identity rather than request
  metadata
- keep ordinary authorization and approval checks on every sensitive tool
- use application idempotency keys for side-effecting tools
- retain TLS and MCP authorization for remote transports

See the core library's `docs/MCP.md` for the envelope format, policy API,
limits, and explicit non-goals.
