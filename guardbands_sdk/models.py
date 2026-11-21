"""Typed response models for the Guard Bands SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WrapResponse:
    wrapped_content: str
    nonce: str
    content_hash: str


@dataclass(frozen=True)
class VerifyResponse:
    valid: bool
    content: str | None = None
    error: str | None = None
    nonce: str | None = None
    key_id: str | None = None
    version: str | None = None


@dataclass(frozen=True)
class CostEstimate:
    model: str
    method: str
    currency: str
    input_tokens_estimate: int
    output_tokens_budget: int
    estimated_input_cost_usd: float
    estimated_output_cost_usd: float
    estimated_total_cost_usd: float
    threshold_usd: float
    threshold_exceeded: bool
    requires_confirmation: bool
    pricing: dict[str, Any]


@dataclass(frozen=True)
class ChatResponse:
    response: str
    model: str
    usage: dict[str, Any]
    cost: dict[str, Any] | None = None


@dataclass(frozen=True)
class IngestResponse:
    wrapped_content: str
    context: dict[str, Any]

    def as_document(self) -> WrappedDocument:
        return WrappedDocument(
            wrapped_content=self.wrapped_content,
            context=self.context,
        )


@dataclass(frozen=True)
class WrappedDocument:
    wrapped_content: str
    context: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return {
            "wrapped_content": self.wrapped_content,
            "context": self.context,
        }


@dataclass(frozen=True)
class ExecuteResponse:
    action: str
    allowed: bool
    documents_verified: int
    content_length: int | None = None
    summary: str | None = None
    message: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
