"""Pluggable secret resolution.

The application reads secret-bearing settings (``SECRET_KEY``,
``GUARD_BAND_KEYS``, API tokens) through a small provider seam so the same code
runs whether secrets come from the environment, AWS Secrets Manager, or
HashiCorp Vault.

Design rules:
- ``env`` is the default and always available — every secrets manager can also
  inject via the environment at the deployment layer (Vault Agent, ECS task
  secrets, Kubernetes External Secrets), so no SDK is required for that path.
- The AWS and Vault SDKs (``boto3`` / ``hvac``) are optional dependencies,
  imported lazily. Install with ``pip install guard-bands-reference[aws]`` or
  ``guard-bands-reference[vault]``.
- "Not found" returns the caller's default; a backend/credential error is
  raised loudly so misconfiguration fails closed rather than silently blank.
"""

from __future__ import annotations

import os
from typing import Protocol


class SecretResolutionError(RuntimeError):
    """Raised when a secrets backend is misconfigured or unreachable."""


class SecretProvider(Protocol):
    def get_secret(self, name: str, default: str | None = None) -> str | None: ...


class EnvSecretProvider:
    """Read secrets from environment variables (default, no dependencies)."""

    def get_secret(self, name: str, default: str | None = None) -> str | None:
        return os.getenv(name, default)


class AwsSecretsManagerProvider:
    """Resolve secrets from AWS Secrets Manager.

    Each logical name maps to a secret id ``{prefix}{name}`` storing the raw
    string value. Values are cached for the process lifetime.
    """

    def __init__(self, prefix: str = "", region_name: str | None = None,
                 endpoint_url: str | None = None, client=None) -> None:
        self._prefix = prefix
        self._region_name = region_name
        self._endpoint_url = endpoint_url
        self._client = client
        self._cache: dict[str, str | None] = {}

    def _get_client(self):
        if self._client is None:
            try:
                import boto3  # optional dependency
            except ImportError as exc:  # pragma: no cover - import guard
                raise SecretResolutionError(
                    "SECRETS_BACKEND=aws requires boto3. Install with: "
                    "pip install 'guard-bands-reference[aws]'"
                ) from exc
            self._client = boto3.client(
                "secretsmanager",
                region_name=self._region_name,
                endpoint_url=self._endpoint_url,
            )
        return self._client

    def get_secret(self, name: str, default: str | None = None) -> str | None:
        if name in self._cache:
            return self._cache[name]
        secret_id = f"{self._prefix}{name}"
        client = self._get_client()
        try:
            response = client.get_secret_value(SecretId=secret_id)
        except Exception as exc:  # noqa: BLE001 - normalize SDK errors
            if type(exc).__name__ == "ResourceNotFoundException":
                self._cache[name] = default
                return default
            raise SecretResolutionError(
                f"Failed to resolve secret '{secret_id}' from AWS Secrets Manager: {exc}"
            ) from exc
        value = response.get("SecretString")
        self._cache[name] = value
        return value


class VaultProvider:
    """Resolve secrets from a HashiCorp Vault KV v2 store.

    Reads path ``{mount}/{prefix}{name}`` and returns the ``value`` field.
    """

    def __init__(self, url: str | None = None, token: str | None = None,
                 mount_point: str = "secret", prefix: str = "guard-bands/",
                 field: str = "value", client=None) -> None:
        self._url = url
        self._token = token
        self._mount_point = mount_point
        self._prefix = prefix
        self._field = field
        self._client = client
        self._cache: dict[str, str | None] = {}

    def _get_client(self):
        if self._client is None:
            try:
                import hvac  # optional dependency
            except ImportError as exc:  # pragma: no cover - import guard
                raise SecretResolutionError(
                    "SECRETS_BACKEND=vault requires hvac. Install with: "
                    "pip install 'guard-bands-reference[vault]'"
                ) from exc
            self._client = hvac.Client(url=self._url, token=self._token)
        return self._client

    def get_secret(self, name: str, default: str | None = None) -> str | None:
        if name in self._cache:
            return self._cache[name]
        path = f"{self._prefix}{name}"
        client = self._get_client()
        try:
            secret = client.secrets.kv.v2.read_secret_version(
                path=path, mount_point=self._mount_point
            )
        except Exception as exc:  # noqa: BLE001 - normalize SDK errors
            if type(exc).__name__ == "InvalidPath":
                self._cache[name] = default
                return default
            raise SecretResolutionError(
                f"Failed to resolve secret '{path}' from Vault: {exc}"
            ) from exc
        value = secret["data"]["data"].get(self._field, default)
        self._cache[name] = value
        return value


def build_secret_provider() -> SecretProvider:
    """Construct the configured secret provider from the environment."""
    backend = os.getenv("SECRETS_BACKEND", "env").strip().lower()
    if backend in ("", "env"):
        return EnvSecretProvider()
    if backend == "aws":
        return AwsSecretsManagerProvider(
            prefix=os.getenv("SECRETS_AWS_PREFIX", ""),
            region_name=os.getenv("SECRETS_AWS_REGION") or None,
            endpoint_url=os.getenv("SECRETS_AWS_ENDPOINT_URL") or None,
        )
    if backend == "vault":
        return VaultProvider(
            url=os.getenv("VAULT_ADDR") or None,
            token=os.getenv("VAULT_TOKEN") or None,
            mount_point=os.getenv("SECRETS_VAULT_MOUNT", "secret"),
            prefix=os.getenv("SECRETS_VAULT_PREFIX", "guard-bands/"),
        )
    raise SecretResolutionError(
        f"Unsupported SECRETS_BACKEND: {backend!r} (expected: env, aws, or vault)"
    )
