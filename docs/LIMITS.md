# Limits and Benchmarks

This POC intentionally keeps limits conservative. They are designed to make the security properties easy to inspect rather than to maximize throughput.

## Current Limits

| Area | Current behavior |
|---|---|
| Content size | API request models and FastAPI integration middleware default to 50 KB |
| Protocol version | new bands are signed as marker version `v:2`; verification accepts `v:2` and legacy `v:1` |
| Hash | SHA-256 over UTF-8 content, returned from `/wrap` for audit logging only — not part of verification |
| MAC | HMAC-SHA256 (or Ed25519) over the RFC 8785 canonical JSON payload; the sole integrity guarantee checked during verification |
| Nonce | random URL-safe nonce, validated as 16-128 URL-safe characters |
| Key id | 1-64 characters, limited to letters, numbers, `_`, `.`, and `-` |
| Replay ledger | optional in-memory ledger or SQLite-backed persistent ledger |
| Parser | manual marker scanning for embedded blocks; strict full-block parsing for verification |

## Parser Behavior

Guard Bands avoids using broad regular expressions over arbitrary prompt text. Embedded block extraction uses bounded string scanning so malformed marker-heavy input does not create regular-expression denial-of-service risk.

Full verification rejects:

- missing start or end markers
- malformed marker blocks
- nested Guard Band markers inside wrapped content
- unsupported protocol versions
- duplicate, unknown, or missing marker parameters
- invalid key ids or nonces
- invalid MAC encoding
- MAC mismatch

## Running Local Benchmarks

Run:

```bash
make bench
```

The benchmark script measures:

- wrapping a small document
- verifying a small document
- extracting multiple embedded blocks
- extracting a valid block after many malformed marker starts

Numbers are local-machine diagnostics, not production capacity claims. If this is used in production, benchmark with representative document sizes, concurrency, key resolver latency, audit sinks, replay datastore latency, and deployment hardware.

## Operational Guidance

- Keep content limits explicit at API boundaries.
- Prefer context values with stable identifiers rather than large arbitrary objects.
- Use a shared replay store if the API runs with multiple workers or replicas.
- Use SQLite replay storage only for single-node pilots.
- Treat verification as a gate before sensitive actions, not as a substitute for authorization.
- Monitor verification failures by tenant, route, policy path, and key id.
