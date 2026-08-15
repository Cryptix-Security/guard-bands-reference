import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.authorization import Principal, authorize_action
from guardbands import GuardBandCrypto


crypto = GuardBandCrypto(
    os.getenv("REFERENCE_APP_SECRET_KEY", "reference-app-dev-secret").encode("utf-8")
)
app = FastAPI(title="Guard Bands Reference Support App")


class PrincipalInput(BaseModel):
    user_id: str
    tenant_id: str
    roles: list[str] = Field(default_factory=list)


class WrapTicketRequest(BaseModel):
    ticket_id: str
    content: str
    principal: PrincipalInput


class WrappedTicketResponse(BaseModel):
    wrapped_content: str
    context: dict


class ToolActionRequest(BaseModel):
    action: str
    wrapped_content: str
    context: dict
    principal: PrincipalInput


def to_principal(principal: PrincipalInput) -> Principal:
    return Principal(
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        roles=frozenset(principal.roles),
    )


@app.post("/tickets/wrap", response_model=WrappedTicketResponse)
async def wrap_ticket(body: WrapTicketRequest):
    context = {
        "request_id": body.ticket_id,
        "tenant_id": body.principal.tenant_id,
        "user": body.principal.user_id,
        "policy_path": "support.read_only",
        "resource_type": "support_ticket",
    }
    return WrappedTicketResponse(
        wrapped_content=crypto.wrap_content(body.content, context),
        context=context,
    )


@app.post("/tool-action")
async def tool_action(body: ToolActionRequest):
    verification = crypto.extract_and_verify(body.wrapped_content, body.context)
    if not verification.get("valid"):
        raise HTTPException(
            status_code=400,
            detail="Guard Band verification failed",
        )

    decision = authorize_action(to_principal(body.principal), body.action, body.context)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)

    if body.action == "summarize_ticket":
        return {
            "action": body.action,
            "allowed": True,
            "content_length": len(verification["content"]),
            "summary": "Verified ticket content accepted for read-only summarization.",
        }

    return {
        "action": body.action,
        "allowed": True,
        "message": "Authorized action would be queued for a real tool here.",
    }
