"""HTTP clients for Guard Bands."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from guardbands_sdk.errors import (
    AuthenticationError,
    AuthorizationError,
    CostThresholdExceeded,
    GuardBandsAPIError,
    NotFoundError,
    RateLimitError,
    VerificationFailed,
)
from guardbands_sdk.models import (
    ChatResponse,
    CostEstimate,
    ExecuteResponse,
    IngestResponse,
    VerifyResponse,
    WrappedDocument,
    WrapResponse,
)


class BaseClient:
    """Small wrapper around ``httpx.Client`` with Guard Bands error mapping."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | httpx.Timeout = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        request_headers = dict(headers or {})
        if api_key:
            request_headers.setdefault("Authorization", f"Bearer {api_key}")
        self._owns_client = client is None
        if client is None:
            self._client = httpx.Client(
                base_url=base_url.rstrip("/"),
                headers=request_headers,
                timeout=timeout,
            )
        else:
            self._client = client
            self._client.headers.update(request_headers)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post(path, json=payload)
        if response.is_success:
            return response.json()
        self._raise_api_error(response)

    def _get(self, path: str) -> dict[str, Any]:
        response = self._client.get(path)
        if response.is_success:
            return response.json()
        self._raise_api_error(response)

    def _raise_api_error(self, response: httpx.Response) -> None:
        try:
            body = response.json()
        except ValueError:
            body = response.text
        detail = body.get("detail") if isinstance(body, dict) else body
        message = _detail_message(detail) or f"Guard Bands API returned HTTP {response.status_code}"

        if response.status_code in (401, 407):
            raise AuthenticationError(
                message,
                status_code=response.status_code,
                detail=detail,
                response_body=body,
            )
        if response.status_code == 402:
            estimate = detail.get("cost_estimate") if isinstance(detail, dict) else None
            raise CostThresholdExceeded(
                message,
                status_code=response.status_code,
                detail=detail,
                response_body=body,
                cost_estimate=estimate,
            )
        if response.status_code == 403:
            raise AuthorizationError(
                message,
                status_code=response.status_code,
                detail=detail,
                response_body=body,
            )
        if response.status_code == 404:
            raise NotFoundError(
                message,
                status_code=response.status_code,
                detail=detail,
                response_body=body,
            )
        if response.status_code == 429:
            raise RateLimitError(
                message,
                status_code=response.status_code,
                detail=detail,
                response_body=body,
            )
        if _looks_like_verification_failure(message):
            raise VerificationFailed(
                message,
                status_code=response.status_code,
                detail=detail,
                response_body=body,
            )
        raise GuardBandsAPIError(
            message,
            status_code=response.status_code,
            detail=detail,
            response_body=body,
        )


class GuardBandsClient(BaseClient):
    """Client for the main Guard Bands FastAPI service."""

    def health(self) -> dict[str, Any]:
        return self._get("/health")

    def wrap(
        self,
        content: str,
        *,
        context: Mapping[str, Any] | None = None,
        key_id: str | None = None,
    ) -> WrapResponse:
        payload: dict[str, Any] = {
            "content": content,
            "context": dict(context or {}),
        }
        if key_id is not None:
            payload["key_id"] = key_id
        return WrapResponse(**self._post("/wrap", payload))

    def verify(
        self,
        wrapped_content: str,
        *,
        context: Mapping[str, Any] | None = None,
        raise_on_invalid: bool = False,
    ) -> VerifyResponse:
        body = self._post(
            "/verify",
            {
                "wrapped_content": wrapped_content,
                "context": dict(context or {}),
            },
        )
        result = VerifyResponse(**body)
        if raise_on_invalid and not result.valid:
            raise VerificationFailed(
                result.error or "Guard Band verification failed",
                status_code=200,
                detail=body,
                response_body=body,
            )
        return result

    def estimate_chat_cost(
        self,
        message: str,
        *,
        context: Mapping[str, Any] | None = None,
        max_output_tokens: int | None = None,
    ) -> CostEstimate:
        payload = _chat_payload(
            message,
            context=context,
            max_output_tokens=max_output_tokens,
        )
        return CostEstimate(**self._post("/chat/estimate-cost", payload))

    def chat(
        self,
        message: str,
        *,
        context: Mapping[str, Any] | None = None,
        max_output_tokens: int | None = None,
        approve_estimated_cost: bool = False,
    ) -> ChatResponse:
        payload = _chat_payload(
            message,
            context=context,
            max_output_tokens=max_output_tokens,
            approve_estimated_cost=approve_estimated_cost,
        )
        return ChatResponse(**self._post("/chat", payload))


class DataPlaneClient(BaseClient):
    """Client for ``dual_channel.data_plane``."""

    def health(self) -> dict[str, Any]:
        return self._get("/health")

    def ingest(
        self,
        content: str,
        *,
        source: str,
        request_id: str,
        tenant_id: str,
        user: str,
    ) -> IngestResponse:
        return IngestResponse(
            **self._post(
                "/ingest",
                {
                    "content": content,
                    "source": source,
                    "request_id": request_id,
                    "tenant_id": tenant_id,
                    "user": user,
                },
            )
        )


class ControlPlaneClient(BaseClient):
    """Client for ``dual_channel.control_plane``."""

    def health(self) -> dict[str, Any]:
        return self._get("/health")

    def execute(
        self,
        action: str,
        *,
        principal_user: str,
        tenant_id: str,
        documents: list[WrappedDocument | IngestResponse | Mapping[str, Any]] | None = None,
        principal_role: str = "viewer",
    ) -> ExecuteResponse:
        payload = {
            "action": action,
            "principal_user": principal_user,
            "principal_role": principal_role,
            "tenant_id": tenant_id,
            "documents": [_document_payload(document) for document in documents or []],
        }
        body = self._post("/execute", payload)
        return ExecuteResponse(raw=body, **body)


def _chat_payload(
    message: str,
    *,
    context: Mapping[str, Any] | None = None,
    max_output_tokens: int | None = None,
    approve_estimated_cost: bool | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "message": message,
        "context": dict(context or {}),
    }
    if max_output_tokens is not None:
        payload["max_output_tokens"] = max_output_tokens
    if approve_estimated_cost is not None:
        payload["approve_estimated_cost"] = approve_estimated_cost
    return payload


def _document_payload(
    document: WrappedDocument | IngestResponse | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(document, IngestResponse):
        return document.as_document().to_payload()
    if isinstance(document, WrappedDocument):
        return document.to_payload()
    return {
        "wrapped_content": document["wrapped_content"],
        "context": dict(document["context"]),
    }


def _detail_message(detail: Any) -> str | None:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        if isinstance(detail.get("error"), str):
            return detail["error"]
        if isinstance(detail.get("detail"), str):
            return detail["detail"]
    return None


def _looks_like_verification_failure(message: str) -> bool:
    lowered = message.lower()
    return (
        "verification failed" in lowered
        or "missing start marker" in lowered
        or "mac verification failed" in lowered
        or "not signed by the data plane" in lowered
        or "not bound to the data channel" in lowered
    )
