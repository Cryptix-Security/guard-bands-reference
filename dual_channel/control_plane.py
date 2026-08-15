"""Control-plane service: trusted instructions and tool execution.

This is the only service with a tool surface, and it enforces the channel
separation at the join point:

- Instructions are taken exclusively from this service's authenticated
  request body. Document text is never parsed for instructions.
- Data is accepted only if it carries a valid data-plane signature (key id,
  issuer, and a `channel: data` context binding all authenticated by the
  Ed25519 signature). Raw text, tampered blocks, or blocks minted by anything
  other than the data plane are rejected — fail closed.

The control plane holds only the Ed25519 **public** key
(DUAL_CHANNEL_VERIFY_KEY, resolved through the secret provider — no
development fallback). It can verify bands but is cryptographically unable to
mint them: a compromised control plane cannot forge data-plane provenance.

In a deployment it runs as its own process on its own port:

    uvicorn dual_channel.control_plane:app --port 8002
"""

import sys

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from guardbands import GuardBandCrypto, StaticKeyResolver, load_ed25519_public_key
from app.secrets_provider import build_secret_provider
from dual_channel import DATA_PLANE_ISSUER, DATA_PLANE_KEY_ID

KEYGEN_HINT = (
    "Generate a keypair with: make dual-channel-keys "
    "(or: python3 -c \"from guardbands import generate_ed25519_keypair as g; "
    "priv, pub = g(); print(priv); print(pub)\")"
)


def load_verify_key():
    """Resolve the data plane's Ed25519 public key. Fail closed if absent."""
    encoded = build_secret_provider().get_secret("DUAL_CHANNEL_VERIFY_KEY", "") or ""
    if not encoded:
        sys.exit(
            "FATAL: DUAL_CHANNEL_VERIFY_KEY is not set. The control plane has "
            f"no development fallback key. {KEYGEN_HINT}"
        )
    try:
        return load_ed25519_public_key(encoded)
    except Exception:
        sys.exit(
            "FATAL: DUAL_CHANNEL_VERIFY_KEY is not a valid base64url raw "
            f"Ed25519 public key. {KEYGEN_HINT}"
        )


# Verification-only resolver: this service cannot sign bands at all.
crypto = GuardBandCrypto(
    key_resolver=StaticKeyResolver({DATA_PLANE_KEY_ID: load_verify_key()}, DATA_PLANE_KEY_ID)
)
app = FastAPI(title="Guard Bands Control Plane", version="0.2.0")

READ_ONLY_ACTIONS = {"summarize_document"}
SENSITIVE_ACTIONS = {"issue_refund"}
ROLE_ACTIONS = {
    "viewer": READ_ONLY_ACTIONS,
    "operator": READ_ONLY_ACTIONS | SENSITIVE_ACTIONS,
}


class WrappedDocument(BaseModel):
    wrapped_content: str
    context: dict


class ExecuteRequest(BaseModel):
    # The instruction channel: action selection happens here and only here.
    action: str = Field(..., max_length=100)
    principal_user: str = Field(..., max_length=200)
    principal_role: str = Field(default="viewer", max_length=50)
    tenant_id: str = Field(..., max_length=100)
    documents: list[WrappedDocument] = Field(default_factory=list)


def _verify_data_plane_document(document: WrappedDocument, tenant_id: str) -> str:
    """Admit a document only if it provably came through the data plane."""
    result = crypto.extract_and_verify(document.wrapped_content, document.context)
    if not result.get("valid"):
        raise HTTPException(
            status_code=400,
            detail=f"Data-plane verification failed: {result.get('error')}",
        )
    if result["key_id"] != DATA_PLANE_KEY_ID or result["issuer"] != DATA_PLANE_ISSUER:
        raise HTTPException(
            status_code=400,
            detail="Document was not signed by the data plane",
        )
    if document.context.get("channel") != "data":
        raise HTTPException(
            status_code=400,
            detail="Document is not bound to the data channel",
        )
    if document.context.get("tenant_id") != tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Document tenant does not match request tenant",
        )
    return result["content"]


@app.post("/execute")
async def execute(body: ExecuteRequest):
    # 1. Authorize the instruction. It came from this authenticated channel;
    #    nothing inside a document can select or escalate the action.
    allowed_actions = ROLE_ACTIONS.get(body.principal_role, set())
    if body.action not in ROLE_ACTIONS["operator"]:
        raise HTTPException(status_code=400, detail=f"Unknown action: {body.action}")
    if body.action not in allowed_actions:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{body.principal_role}' is not allowed to perform: {body.action}",
        )

    # 2. Admit data only with a valid data-plane signature — fail closed.
    verified_contents = [
        _verify_data_plane_document(document, body.tenant_id)
        for document in body.documents
    ]

    # 3. Execute. Document text is inert data: it is summarized or attached,
    #    never interpreted as an instruction.
    if body.action == "summarize_document":
        return {
            "action": body.action,
            "allowed": True,
            "documents_verified": len(verified_contents),
            "content_length": sum(len(content) for content in verified_contents),
            "summary": "Verified data-plane content accepted for read-only summarization.",
        }

    return {
        "action": body.action,
        "allowed": True,
        "documents_verified": len(verified_contents),
        "message": (
            "Authorized action would be queued for a real tool here. "
            "Action selection came from the control channel only."
        ),
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "plane": "control"}
