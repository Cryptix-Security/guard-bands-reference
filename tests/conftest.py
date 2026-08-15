import os

os.environ.setdefault("SECRET_KEY", "pytest-secret-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "pytest-anthropic-key")
os.environ.setdefault("SSO_ENABLED", "false")

# The dual-channel services have no development fallback keys (fail closed),
# so tests inject a fresh matching Ed25519 keypair. Set both together so an
# externally-provided half can never be paired with a generated one.
if not (os.environ.get("DUAL_CHANNEL_SIGNING_KEY") and os.environ.get("DUAL_CHANNEL_VERIFY_KEY")):
    from guardbands import generate_ed25519_keypair

    _private_b64, _public_b64 = generate_ed25519_keypair()
    os.environ["DUAL_CHANNEL_SIGNING_KEY"] = _private_b64
    os.environ["DUAL_CHANNEL_VERIFY_KEY"] = _public_b64
