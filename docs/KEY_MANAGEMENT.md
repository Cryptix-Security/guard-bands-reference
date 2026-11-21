# Key Management

The Guard Bands mechanism is documented in the core library repository. This repository pins core `v0.10.0` (see `pyproject.toml`), so the links below point at the core docs for that tag. Update them when the pin moves.

- [Core key management expectations](https://github.com/Cryptix-Security/guard-bands/blob/v0.10.0/docs/KEY_MANAGEMENT.md): what the library expects from applications, production expectations, rotation grace windows, and the `KeyResolver` boundary.

This page covers only how the reference stack loads and rotates keys.

## Reference stack configuration

- `SECRET_KEY` must be set before startup. The API intentionally exits if it is missing.
- Generate a local evaluation key with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

- Keep `.env` out of version control.
- Use different keys for development, test, staging, and production.
- `KEY_ID` (default `key001`) selects the active signing key. It is public metadata, not the secret.
- Optionally set `GUARD_BAND_KEYS` to a JSON object of key id to secret for rotation-style verification. When it is unset, the API uses `SECRET_KEY` under `KEY_ID`:

```bash
GUARD_BAND_KEYS='{"key001":"active-secret","key000":"retired-secret"}'
KEY_ID=key001
```

- `SECRET_KEY` and `GUARD_BAND_KEYS` resolve through the pluggable secret provider, so they can come from the environment, AWS Secrets Manager, or Vault. See [`SECRETS.md`](SECRETS.md).

The API builds the core `StaticKeyResolver` from these settings at startup. The dual-channel services use separate Ed25519 keys; see [`DUAL_CHANNEL.md`](DUAL_CHANNEL.md).
