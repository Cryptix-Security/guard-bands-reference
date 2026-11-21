"""Deployment configuration for the core library's replay ledgers."""

from typing import Any

from guardbands import (
    NonceReplayLedger,
    ReplayLedger,
    SQLiteReplayLedger,
)
from guardbands import (
    apply_replay_protection as apply_core_replay_protection,
)

from app.config import settings


def create_replay_ledger() -> ReplayLedger | None:
    if not settings.REPLAY_PROTECTION_ENABLED:
        return None
    if settings.REPLAY_LEDGER_BACKEND == "memory":
        return NonceReplayLedger(settings.REPLAY_WINDOW_SECONDS)
    if settings.REPLAY_LEDGER_BACKEND == "sqlite":
        return SQLiteReplayLedger(
            path=settings.REPLAY_LEDGER_PATH,
            ttl_seconds=settings.REPLAY_WINDOW_SECONDS,
        )
    raise ValueError(f"Unsupported replay ledger backend: {settings.REPLAY_LEDGER_BACKEND}")


replay_ledger = create_replay_ledger()


def apply_replay_protection(result: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Apply the deployment-selected ledger to a verification result."""
    return apply_core_replay_protection(result, context, replay_ledger)
