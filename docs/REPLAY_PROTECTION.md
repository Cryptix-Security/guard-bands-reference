# Replay Protection

The Guard Bands mechanism is documented in the core library repository. This repository pins core `v0.10.0` (see `pyproject.toml`), so the links below point at the core docs for that tag. Update them when the pin moves.

- [Core replay-protection examples](https://github.com/Cryptix-Security/guard-bands/blob/v0.10.0/docs/REPLAY_PROTECTION.md): context-bound replay protection, the nonce ledger pattern, expiration buckets, and tool-path binding.

This page covers only how the reference API configures replay protection.

## Reference stack configuration

Replay protection is off by default. Enable the in-memory ledger for local evaluation and tests:

```bash
REPLAY_PROTECTION_ENABLED=true
REPLAY_LEDGER_BACKEND=memory
REPLAY_WINDOW_SECONDS=900
```

Use `sqlite` to persist consumed nonces across restarts for a single-node pilot:

```bash
REPLAY_PROTECTION_ENABLED=true
REPLAY_LEDGER_BACKEND=sqlite
REPLAY_LEDGER_PATH=data/replay-ledger.sqlite3
REPLAY_WINDOW_SECONDS=900
```

`app/replay.py` builds the matching core ledger (`NonceReplayLedger` or `SQLiteReplayLedger`) at startup and applies it in `/verify`.

Production deployments with multiple workers or replicas should use a shared datastore with atomic inserts or uniqueness constraints. The SQLite backend is durable, but it is not a substitute for a shared Redis or Postgres ledger across multiple API replicas. This stack does not ship one yet.
