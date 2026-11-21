# Canonical Context Serialization

The Guard Bands mechanism is documented in the core library repository. This repository pins core `v0.10.0` (see `pyproject.toml`), so the links below point at the core docs for that tag. Update them when the pin moves.

- [Core canonical context serialization](https://github.com/Cryptix-Security/guard-bands/blob/v0.10.0/docs/CONTEXT_SERIALIZATION.md): the signed payload, canonical JSON rules, context design guidance, and the marker format.

The reference stack does not change serialization. It passes caller-supplied context from `/wrap` and `/verify` straight to the core library. For the context fields this stack binds, see [`API_EXAMPLES.md`](API_EXAMPLES.md) and [`REPLAY_PROTECTION.md`](REPLAY_PROTECTION.md).
