"""Data-plane service: untrusted content intake.

This service is deliberately incapable of executing anything. It exposes no
tool registry, no instruction endpoint, and no model access. Its only job is
to take untrusted content and return a signed inert block. In a deployment it
runs as its own process on its own port (or host/network segment):

    uvicorn dual_channel.data_plane:app --port 8001

The data plane is the sole holder of the Ed25519 private key
(DUAL_CHANNEL_SIGNING_KEY, resolved through the secret provider — no
development fallback). Everything it emits is bound to `channel: data` and
signed with the data-plane key id and issuer, so a downstream control plane
can cryptographically prove which channel a piece of content entered through.
"""

import sys

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from guardbands import GuardBandCrypto, StaticKeyResolver, load_ed25519_private_key
from app.models import CONTENT_MAX_BYTES
from app.secrets_provider import build_secret_provider
from dual_channel import DATA_PLANE_ISSUER, DATA_PLANE_KEY_ID

KEYGEN_HINT = (
    "Generate a keypair with: make dual-channel-keys "
    "(or: python3 -c \"from guardbands import generate_ed25519_keypair as g; "
    "priv, pub = g(); print(priv); print(pub)\")"
)


def load_signing_key():
    """Resolve the data plane's Ed25519 private key. Fail closed if absent."""
    encoded = build_secret_provider().get_secret("DUAL_CHANNEL_SIGNING_KEY", "") or ""
    if not encoded:
        sys.exit(
            "FATAL: DUAL_CHANNEL_SIGNING_KEY is not set. The data plane has no "
            f"development fallback key. {KEYGEN_HINT}"
        )
    try:
        return load_ed25519_private_key(encoded)
    except Exception:
        sys.exit(
            "FATAL: DUAL_CHANNEL_SIGNING_KEY is not a valid base64url raw "
            f"Ed25519 private key. {KEYGEN_HINT}"
        )


crypto = GuardBandCrypto(
    key_resolver=StaticKeyResolver({DATA_PLANE_KEY_ID: load_signing_key()}, DATA_PLANE_KEY_ID)
)
app = FastAPI(title="Guard Bands Data Plane", version="0.2.0")


class IngestRequest(BaseModel):
    content: str = Field(..., max_length=CONTENT_MAX_BYTES)
    source: str = Field(..., max_length=200)
    request_id: str = Field(..., max_length=100)
    tenant_id: str = Field(..., max_length=100)
    user: str = Field(..., max_length=200)


class IngestResponse(BaseModel):
    wrapped_content: str
    context: dict


@app.post("/ingest", response_model=IngestResponse)
async def ingest(body: IngestRequest):
    """Wrap untrusted content into a signed inert block. Nothing more."""
    # Reject marker smuggling at the entry point rather than letting it fail
    # later as a nested-marker verification error downstream.
    if "⟪INERT:START" in body.content or "⟪INERT:END" in body.content:
        raise HTTPException(
            status_code=400,
            detail="Content may not contain guard band markers",
        )

    context = {
        "request_id": body.request_id,
        "tenant_id": body.tenant_id,
        "user": body.user,
        "source": body.source,
        # The channel is bound into the signature: this block provably
        # entered through the data plane and nowhere else.
        "channel": "data",
        "policy_path": "dual_channel.read_only",
    }
    wrapped = crypto.wrap_content(body.content, context, issuer=DATA_PLANE_ISSUER)
    return IngestResponse(wrapped_content=wrapped, context=context)


@app.get("/health")
async def health():
    return {"status": "healthy", "plane": "data"}
