# Secrets Management

Secret-bearing settings resolve through a pluggable provider so the same code
runs whether secrets come from the environment, AWS Secrets Manager, or
HashiCorp Vault. Select the backend with `SECRETS_BACKEND`.

Resolved through the provider: `SECRET_KEY`, `GUARD_BAND_KEYS`,
`ANTHROPIC_API_KEY`, `LOG_POSTGRES_DSN`, `LOG_SPLUNK_HEC_TOKEN`. Non-secret
settings (ports, flags, model name) always come from the environment.

## `env` (default)

```bash
SECRETS_BACKEND=env
```

Reads each secret from the matching environment variable. This is also the path
for "inject at deploy time" setups — Vault Agent, AWS ECS task secrets, or the
Kubernetes External Secrets Operator all populate the environment, so no SDK is
required.

## `aws` — AWS Secrets Manager

```bash
pip install 'guard-bands-reference[aws]'
SECRETS_BACKEND=aws
SECRETS_AWS_PREFIX=prod/guard-bands/     # optional
SECRETS_AWS_REGION=us-east-1             # optional (else default chain)
```

Each logical name maps to secret id `{SECRETS_AWS_PREFIX}{NAME}` storing the raw
string value — e.g. `prod/guard-bands/SECRET_KEY`. Credentials come from the
standard AWS chain (instance role, env, or profile). A missing secret falls back
to any default; a credential/permission error fails loudly (fail closed).

> Tip: SSM Parameter Store (SecureString) is a near-free alternative for small
> teams; Secrets Manager adds native rotation, which pairs with the `kid`-based
> key rotation in `GUARD_BAND_KEYS`.

## `vault` — HashiCorp Vault (KV v2)

```bash
pip install 'guard-bands-reference[vault]'
SECRETS_BACKEND=vault
VAULT_ADDR=https://vault.example:8200
VAULT_TOKEN=<token or use an auth method / agent>
SECRETS_VAULT_MOUNT=secret               # optional
SECRETS_VAULT_PREFIX=guard-bands/        # optional
```

Reads path `{MOUNT}/{PREFIX}{NAME}` and returns the `value` field — e.g.
`secret/guard-bands/SECRET_KEY` with `value=<secret>`.

## Notes

- The base install pulls in no cloud SDK; `boto3`/`hvac` are optional extras.
- Values are cached for the process lifetime (fetched once at startup).
- Keep secrets out of source control and images regardless of backend; back up
  `SECRET_KEY` and `GUARD_BAND_KEYS` — losing them makes existing bands
  unverifiable.
