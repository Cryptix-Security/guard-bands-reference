import json
import logging

import httpx

from app.audit import AuditEvent
from app.sinks.base import AuditSink

logger = logging.getLogger(__name__)


class SplunkHECSink(AuditSink):
    """Splunk HTTP Event Collector sink.

    Requires a HEC token with write access to the target index.
    Set LOG_SPLUNK_SSL_VERIFY=false to disable cert verification for on-prem installs.
    """

    def __init__(
        self, hec_url: str, token: str, index: str, source: str, ssl_verify: bool = True
    ) -> None:
        self._url = hec_url.rstrip("/") + "/services/collector/event"
        self._headers = {
            "Authorization": f"Splunk {token}",
            "Content-Type": "application/json",
        }
        self._index = index
        self._source = source
        self._ssl_verify = ssl_verify
        self._client: httpx.AsyncClient | None = None

    async def startup(self) -> None:
        self._client = httpx.AsyncClient(timeout=5.0, verify=self._ssl_verify)
        logger.info("Splunk HEC sink configured → %s (index=%s)", self._url, self._index)

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()

    async def emit(self, event: AuditEvent) -> None:
        if not self._client:
            return
        payload = {
            "time": event.timestamp.timestamp(),
            "index": self._index,
            "source": self._source,
            "sourcetype": "_json",
            "event": {
                "id": event.id,
                "event_type": event.event_type,
                "success": event.success,
                "ip": event.ip,
                "user_id": event.user_id,
                "duration_ms": round(event.duration_ms, 2),
                **event.details,
            },
        }
        resp = await self._client.post(
            self._url, headers=self._headers, content=json.dumps(payload)
        )
        resp.raise_for_status()
