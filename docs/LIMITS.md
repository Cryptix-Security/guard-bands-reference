# Limits and Benchmarks

The Guard Bands mechanism is documented in the core library repository. This repository pins core `v0.10.0` (see `pyproject.toml`), so the links below point at the core docs for that tag. Update them when the pin moves.

- [Core limits](https://github.com/Cryptix-Security/guard-bands/blob/v0.10.0/docs/LIMITS.md): protocol version, MAC, nonce and key id rules, replay ledgers, MCP payload size, and parser behavior.

This page covers only the limits and benchmarks specific to the reference stack.

## Reference stack limits

| Area | Behavior |
|---|---|
| API request size | `/wrap` content and `/chat` message fields are capped at 50,000 characters (`app/models.py`); the dual-channel data plane uses the same cap |
| Content hash | SHA-256 over UTF-8 content, returned from `/wrap` for audit logging only. It is not part of verification |
| Band lifetime | `GUARD_BAND_TTL_SECONDS` (default 900) sets the authenticated `iat`/`exp` window on wrapped bands |
| Replay ledger | off by default; memory or SQLite when enabled (see [`REPLAY_PROTECTION.md`](REPLAY_PROTECTION.md)) |

## Running local benchmarks

```bash
make bench
```

The benchmark script (`scripts/benchmark_parser.py`) measures:

- wrapping a small document
- verifying a small document
- extracting multiple embedded blocks
- extracting a valid block after many malformed marker starts

Numbers are local-machine diagnostics, not production capacity claims. If this is used in production, benchmark with representative document sizes, concurrency, key resolver latency, audit sinks, replay datastore latency, and deployment hardware.

## Operational guidance

- Keep content limits explicit at API boundaries.
- Prefer context values with stable identifiers rather than large arbitrary objects.
- Use a shared replay store if the API runs with multiple workers or replicas.
- Use SQLite replay storage only for single-node pilots.
- Treat verification as a gate before sensitive actions, not as a substitute for authorization.
- Monitor verification failures by tenant, route, policy path, and key id.
