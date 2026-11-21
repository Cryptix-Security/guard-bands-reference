from fastapi.testclient import TestClient

import app.main as main
from app.audit import audit


class _CapturingSink:
    """Audit sink that records emitted events for assertions."""

    def __init__(self):
        self.events = []

    async def emit(self, event):
        self.events.append(event)

    async def startup(self):
        pass

    async def shutdown(self):
        pass


def test_chat_audit_event_records_actual_cost(monkeypatch):
    async def fake_chat(
        user_message, context=None, max_output_tokens=None, approve_estimated_cost=False
    ):
        return {
            "success": True,
            "response": "ok",
            "model": "fake-model",
            "usage": {"input_tokens": 10, "output_tokens": 5},
            "cost": {
                "preflight_estimate": {"estimated_total_cost_usd": 0.001},
                "actual": {
                    "total_cost_usd": 0.00042,
                    "input_tokens": 10,
                    "output_tokens": 5,
                },
            },
        }

    monkeypatch.setattr(main.llm_service, "chat", fake_chat)

    sink = _CapturingSink()
    try:
        with TestClient(main.app) as client:
            audit.add_sink(sink)
            response = client.post("/chat", json={"message": "hello", "context": {}})

        assert response.status_code == 200
        # The final actual cost is surfaced to the caller in the response...
        assert response.json()["cost"]["actual"]["total_cost_usd"] == 0.00042

        # ...and recorded in the audit trail for per-user cost attribution.
        chat_events = [e for e in sink.events if e.event_type == "chat"]
        assert chat_events, "no chat audit event was emitted"
        details = chat_events[-1].details
        assert details["actual_cost_usd"] == 0.00042
        assert details["estimated_cost_usd"] == 0.001
    finally:
        if sink in audit._sinks:
            audit._sinks.remove(sink)
