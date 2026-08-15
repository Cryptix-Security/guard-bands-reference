# Guard Bands - Quick Start Guide

**Proof-of-Concept Implementation**

This guide walks you through building and running the Guard Bands POC that demonstrates cryptographic protection against prompt injection attacks.

> **Evaluating this project?** The stack runs end-to-end with a single `docker compose up --build`. The one required step before anything starts is generating a `SECRET_KEY` — the app hard-fails at startup without one (see [Configure Environment](#2-configure-environment) below). Everything else has working defaults for local evaluation. Dev secrets are intentional placeholders; see [Production Considerations](#production-considerations) before deploying anywhere real.

## Prerequisites

- **Python 3.11+** (CI runs on 3.11 and 3.12; Docker uses 3.12)
- **Anthropic API Key** - Using Claude for this POC
- **Git** (for cloning the repository)
- **Docker + Docker Compose** (optional for local Postgres; required for the full SSO stack)

## Installation

### 1. Clone and Setup

```bash
git clone https://github.com/Cryptix-Security/guard-bands-reference.git
cd guard-bands-reference

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install runtime dependencies
pip3 install -r requirements.txt

# Install test/development dependencies
pip3 install -r requirements-dev.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

> **Required — the app will not start without this:** generate a `SECRET_KEY` and paste it into `.env`:
> ```bash
> python3 -c "import secrets; print(secrets.token_urlsafe(32))"
> ```

Edit `.env` and set at minimum:

```
SECRET_KEY=<output from the command above>
KEY_ID=key001
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
DEBUG=false

# CORS — comma-separated allowed origins
ALLOWED_ORIGINS=http://localhost:3000

# Optional preflight LLM cost guard
LLM_MAX_OUTPUT_TOKENS=2048
COST_GUARD_ENABLED=true
COST_GUARD_THRESHOLD_USD=1.00
COST_GUARD_INPUT_USD_PER_MTOK=1.00
COST_GUARD_OUTPUT_USD_PER_MTOK=5.00

# Optional replay ledger for single-use verification semantics
REPLAY_PROTECTION_ENABLED=false
REPLAY_LEDGER_BACKEND=memory
REPLAY_LEDGER_PATH=data/replay-ledger.sqlite3
REPLAY_WINDOW_SECONDS=900
```

**Audit logging** (optional but recommended):

```
# Local Postgres — start with: docker compose up -d
LOG_POSTGRES_DSN=postgresql://guard_bands:changeme@localhost:5432/guard_bands

# Splunk HEC — leave blank to disable
LOG_SPLUNK_HEC_URL=https://splunk.example.com:8088
LOG_SPLUNK_HEC_TOKEN=
LOG_SPLUNK_INDEX=guard_bands
```

Audit events are **always** written as structured JSON lines to stdout (one object per event) via the built-in console sink. Postgres and Splunk are additive — they receive the same events in parallel. If Postgres is unavailable at startup the app continues with console-only logging rather than crashing.

## Running the POC

Two modes — choose based on what you're testing:

### Option A: Direct (no SSO, rapid dev)

```bash
# Optional: start Postgres for audit logs
docker compose up -d postgres

python3 -m uvicorn app.main:app --reload
# API available at http://localhost:8000
```

### Option B: Full stack (SSO enforced)

```bash
docker compose up --build
# API entry point: http://localhost:4180  (oauth2-proxy)
# Keycloak admin:  http://localhost:8080  (admin / $KEYCLOAK_ADMIN_PASSWORD)
```

Wait for all services to be healthy (~60s first run while Keycloak initialises).

**Interactive API Docs** (Option A only): `http://localhost:8000/docs`

### Authenticating Against the SSO Stack

When running Option B, all requests to port 4180 require a valid Bearer token.

**Step 1 — Get a token from Keycloak (password grant for dev/testing):**

```bash
TOKEN=$(curl -s -X POST \
  http://localhost:8080/realms/guard-bands/protocol/openid-connect/token \
  -d "client_id=guard-bands-api" \
  -d "client_secret=dev-client-secret-change-in-prod" \
  -d "username=testuser" \
  -d "password=testpass123" \
  -d "grant_type=password" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

**Step 2 — Call the API with the token:**

```bash
curl -X POST http://localhost:4180/wrap \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "doc text", "context": {"request_id": "r1", "user": "alice"}}'
```

For production/enterprise clients, use the `client_credentials` grant type instead of `password`. The test user (`testuser` / `testpass123`) exists only in the dev realm import.

### Run the Security Tests

The security checks are now a standard pytest suite and do not require the server to be running:

```bash
cd guard-bands-reference
source .venv/bin/activate
make test
```

**What it tests:**
- ✅ Valid content verification (HMAC-SHA256 and Ed25519)
- ✅ Context tampering protection
- ✅ Content modification detection
- ✅ Forged guard band rejection
- ✅ Unwrapped content handling
- ✅ Canonical context serialization
- ✅ Nonce tampering protection
- ✅ Marker-metadata tampering (key id, issuer, expiry)
- ✅ Cross-algorithm confusion and verification-only keys
- ✅ Property-based fuzzing of the marker parser
- ✅ API wrap/verify flows
- ✅ LLM tool-call enforcement
- ✅ FastAPI middleware enforcement
- ✅ malformed marker extraction hardening
- ✅ persistent SQLite replay ledger
- ✅ reference app authorization flow
- ✅ two-channel invariants (forged issuer, wrong channel, fail-closed startup)
- ✅ secret-provider resolution (env, AWS, Vault)
- ✅ chat cost guardrails and per-user cost logging
- ✅ Python SDK clients

### Run the FastAPI Demo

This demo does not require an LLM API key. It exercises the FastAPI app through its test client and shows successful verification, tamper rejection, and wrong-context replay rejection.

```bash
make demo
```

### Run the Reference App Demo

This demo shows a support-ticket workflow where Guard Bands verification must pass before authorization decides whether a tool action is allowed.

```bash
make reference-demo
```

### Run the Dual-Channel Demo

This demo runs untrusted data and trusted instructions through two separate services (deployable on different ports) with a cryptographic join point: the control plane only accepts data signed by the data plane, and instructions never come from content. See [`docs/DUAL_CHANNEL.md`](docs/DUAL_CHANNEL.md).

```bash
make dual-channel-demo
```

To deploy the two planes as separate containers on disjoint networks with split
Ed25519 key delivery (the data plane signs, the control plane can only verify):

```bash
make dual-channel-keys > .env.dual-channel
docker compose -f deploy/docker-compose.dual-channel.yml \
  --env-file .env.dual-channel up --build
```

### Use the Python SDK

A thin client for the HTTP APIs (the server remains the security boundary):

```bash
python -m pip install -e .
```

```python
from guardbands_sdk import GuardBandsClient

with GuardBandsClient("http://localhost:8000") as guardbands:
    wrapped = guardbands.wrap("untrusted document text", context={"request_id": "req-001"})
    verified = guardbands.verify(wrapped.wrapped_content, context={"request_id": "req-001"})
```

See [`docs/PYTHON_SDK.md`](docs/PYTHON_SDK.md) for the chat/cost flow, the
two-channel clients, bearer-token auth, and error handling.

### Run Parser Benchmarks

```bash
make bench
```

### Run the LLM Demo

```bash
python3 demo_llm_attack.py
```

**What it demonstrates:**
1. Prompt injection without protection
2. Same attack with Guard Bands enabled
3. Cryptographic verification process
4. Safe extraction of legitimate data

## API Endpoints

### Wrap Content

Wrap untrusted content with cryptographic guard bands:

```bash
curl -X POST "http://localhost:8000/wrap" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User document content here",
    "context": {"request_id": "req-001", "user": "alice"}
  }'
```

**Response:**
```json
{
  "wrapped_content": "⟪INERT:START:v:1:r:nonce:iat:issued:exp:expiry⟫\nUser document content here\n⟪INERT:END:mac:signature:kid:key001:iss:issuer⟫",
  "nonce": "abc123...",
  "content_hash": "xyz789..."
}
```

### Verify Guard Bands

Verify cryptographic signatures:

```bash
curl -X POST "http://localhost:8000/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "wrapped_content": "⟪INERT:START:v:1:...⟫content⟪INERT:END:...⟫",
    "context": {"request_id": "req-001", "user": "alice"}
  }'
```

**Response:**
```json
{
  "valid": true,
  "content": "User document content here",
  "nonce": "abc123...",
  "key_id": "key001",
  "version": "1"
}
```

### Chat with Protected LLM

Send queries to Claude with guard band awareness:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Analyze this document: ⟪INERT:START:v:1:...⟫content⟪INERT:END:...⟫",
    "context": {"request_id": "req-001", "user": "alice"}
  }'
```

## Project Architecture

```
guard-bands/
├── app/
│   ├── main.py              # FastAPI server & endpoints
│   ├── crypto.py            # HMAC signing & verification
│   ├── llm.py               # Claude integration & tools
│   ├── models.py            # Pydantic data models
│   ├── config.py            # Environment configuration
│   ├── authorization.py     # Example role/action authorization checks
│   ├── replay.py            # Memory and SQLite replay ledgers
│   ├── audit.py             # AuditEvent + AuditLogger (fan-out)
│   ├── middleware/
│   │   └── auth.py          # SSO header middleware (reads oauth2-proxy headers)
│   └── sinks/
│       ├── base.py          # Abstract AuditSink
│       ├── console.py       # Structured JSON → stdout (always on)
│       ├── postgres.py      # PostgreSQL sink (asyncpg)
│       └── splunk.py        # Splunk HEC sink
├── keycloak/
│   └── realm-export.json    # Auto-imported realm (client + test user)
├── tests/                   # Pytest security, API, and tool-enforcement tests
├── docs/                    # API examples and operational guidance
├── integrations/            # FastAPI and RAG integration helpers
├── reference_app/           # Small support-ticket reference workflow
├── scripts/                 # Local demo and benchmark scripts
├── test_manual.py           # Legacy wrapper for python3 -m pytest
├── demo_llm_attack.py       # Interactive LLM demo
├── Makefile                 # Local test, demo, benchmark, and run shortcuts
├── Dockerfile               # App container image
├── docker-compose.yml       # Full stack: Postgres, Keycloak, oauth2-proxy, app
├── requirements.txt         # Runtime Python dependencies
├── requirements-dev.txt     # Test/development dependencies
├── pyproject.toml           # Python package metadata
├── .env.example             # Configuration template
└── .gitignore               # Git ignore rules
```

## How It Works

### 1. Content Wrapping

When untrusted content enters the system:

```python
# Server wraps content with cryptographic markers
wrapped = wrap_content(
    content="User document",
    context={"request_id": "req-001", "user": "alice"}
)
```

The result includes:
- **Nonce**: Random value for uniqueness
- **Hash**: SHA-256 of content
- **MAC**: HMAC signature binding content + context
- **Key ID**: Identifier for the signing key

### 2. LLM Detection

Claude is trained (via system prompt) to:
- Detect guard band markers
- Treat wrapped content as untrusted
- Call verification before processing

### 3. Verification

The LLM uses a tool to verify:

```python
result = verify_guard_bands(
    wrapped_content=wrapped,
    context={"request_id": "req-001", "user": "alice"}
)
```

Verification checks:
- MAC signature is valid (the sole integrity guarantee — content hash is informational-only and not checked here)
- Protocol version, key id, and issuer are authenticated
- Band has not expired (`iat`/`exp`)
- Context matches exactly

### 4. Safe Processing

Only after successful verification does Claude process the content as legitimate data.

## Security Properties

### What Guard Bands Prevent

✅ **Naive Injection** - Basic command insertion attempts  
✅ **Crafted Boundaries** - Forged guard band markers  
✅ **Context Confusion** - Blurring data vs instructions  
✅ **Replay Attacks** - Reusing markers in wrong context  

### What Guard Bands Reduce

🔸 **Multi-turn Attacks** - Harder with per-turn validation  
🔸 **Social Engineering** - Difficult to trick users  
🔸 **Supply Chain** - Provides verification trail  

### Known Limitations

❌ **Model Compliance** - Cannot prevent all policy violations  
❌ **Key Compromise** - Security depends on key management  
❌ **Semantic Attacks** - Doesn't address misleading legitimate content  

## Troubleshooting

### Port Already in Use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
python3 -m uvicorn app.main:app --reload --port 8001
```

### Module Not Found

```bash
# Activate venv
source venv/bin/activate

# Reinstall dependencies
pip3 install -r requirements.txt
```

### API Key Errors

- Verify key at [console.anthropic.com](https://console.anthropic.com)
- Check `.env` exists in project root
- Ensure no extra spaces in `.env`
- Restart server after editing `.env`

### Verification Failures

- Ensure context matches exactly between wrap and verify
- Check that SECRET_KEY hasn't changed
- Verify content hasn't been modified

### No Audit Events Appearing

Audit events are JSON lines written to **stdout** (not stderr, not a log file). When running with uvicorn they appear interleaved with the access log:

```
{"id": "...", "timestamp": "...", "event_type": "wrap", "success": true, ...}
```

If you see access logs but no JSON lines, check that the `ConsoleSink` is active (it always is) and that your terminal/log collector isn't filtering stdout.

### App Crashes at Startup with Database Error

If `LOG_POSTGRES_DSN` is set but Postgres isn't available yet, the app logs a warning and continues with console-only audit logging — it does **not** crash. If you see a startup failure check `SECRET_KEY` (the only hard-fail on missing config) and your Python/dependency versions.

### `/wrap`, `/verify`, `/chat` Return 500 on Every Request

This was a known bug (now fixed) where the `slowapi` rate limiter couldn't find the Starlette `Request` parameter. If you're running an older version, `git pull` to pick up the fix.

## Example Session

```bash
# Terminal 1 - Start server
$ python3 -m uvicorn app.main:app --reload
INFO: Uvicorn running on http://127.0.0.1:8000

# Terminal 2 - Run demo
$ python3 demo_llm_attack.py

🛡️  GUARD BANDS POC - LLM Security Demo

======== DEMO WITHOUT GUARD BANDS ========
Claude's response: [May or may not be fooled by injection]

======== DEMO WITH GUARD BANDS ========
✓ Content wrapped with cryptographic signatures
✓ Claude detects guard bands
✓ Claude calls verification tool
✓ Verification successful
✓ Legitimate data extracted safely
✗ Malicious instructions ignored

✅ Demo Complete!
```

## Next Steps

1. **Read the main [README](README.md)** for conceptual background
2. **Review [Guard-Bands-Paper.md](Guard-Bands-Paper.md)** for technical details
3. **Explore the [core library](https://github.com/Cryptix-Security/guard-bands)**
   to understand the cryptography
4. **Modify `demo_llm_attack.py`** to test your own attack scenarios
5. **Try different LLM models** by changing the model parameter

## Development

### Adding New Test Cases

Add or edit files in `tests/`:

```python
def test_your_attack():
    assert attack_is_blocked()
```

### Changing the Model

Set `LLM_MODEL` in `.env` — no code change needed:

```
LLM_MODEL=claude-sonnet-4-20250514       # Claude Sonnet 4 (more capable)
LLM_MODEL=claude-3-5-haiku-20241022      # Claude 3.5 Haiku (default, faster for demos)
```

### Customizing Guard Band Format

Develop changes in the core `guard-bands` repository to modify:
- Marker format (⟪INERT:START⟫)
- Hash algorithm (default: SHA-256)
- MAC algorithm (default: HMAC-SHA256)
- Nonce generation

## Production Considerations

This is a POC. For production use, consider:

- **Key rotation** - Implement regular SECRET_KEY updates
- **Key management** - Use proper secrets management (AWS Secrets Manager, etc.)
- **Canonical context design** - Keep context fields stable and security-relevant
- **Replay ledgers** - Use `sqlite` for a single-node pilot or a shared Redis/Postgres ledger for multiple replicas
- **Authorization** - Check tenant, user, role, and policy path before sensitive tools run
- **Cost guardrails** - Set model-specific prices and per-org thresholds before enabling model calls
- **Rate limiting** - Per-user limits already in place; tune thresholds for your traffic
- **HTTPS** - Guard bands don't encrypt; terminate TLS at the load balancer, not oauth2-proxy
- **Time expiration** - Add timestamp validation to nonces to prevent stale replay attacks
- **Production secrets** - Replace `dev-client-secret-change-in-prod` and the cookie secret; rotate regularly
- **Keycloak persistence** - Switch from H2 (dev) to Postgres backend for Keycloak in production
- **Enterprise IdP** - Connect Keycloak to your LDAP/Active Directory or SAML provider via Keycloak identity federation
- **Audit log retention** - Set Postgres table partitioning or Splunk index TTL as appropriate

See also:

- [`docs/API_EXAMPLES.md`](docs/API_EXAMPLES.md)
- [`docs/AUTHORIZATION.md`](docs/AUTHORIZATION.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/COST_GUARD.md`](docs/COST_GUARD.md)
- [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md)
- [`docs/LIMITS.md`](docs/LIMITS.md)
- [`docs/KEY_MANAGEMENT.md`](docs/KEY_MANAGEMENT.md)
- [`docs/PRODUCTION_DEPLOYMENT.md`](docs/PRODUCTION_DEPLOYMENT.md)
- [`docs/REFERENCE_APP.md`](docs/REFERENCE_APP.md)
- [`docs/CONTEXT_SERIALIZATION.md`](docs/CONTEXT_SERIALIZATION.md)
- [`docs/REPLAY_PROTECTION.md`](docs/REPLAY_PROTECTION.md)

## Contributing

Found a vulnerability or have ideas for improvement?

1. Open an issue describing the problem
2. Submit a PR with fixes or enhancements
3. Start a discussion about new features

## Resources

- **Reference deployment**: [github.com/Cryptix-Security/guard-bands-reference](https://github.com/Cryptix-Security/guard-bands-reference)
- **Core library**: [github.com/Cryptix-Security/guard-bands](https://github.com/Cryptix-Security/guard-bands)
- **Paper**: [Guard-Bands-Paper.md](Guard-Bands-Paper.md)
- **Anthropic**: [docs.anthropic.com](https://docs.anthropic.com)
- **FastAPI**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)

## License

MIT License - See [LICENSE](LICENSE) for details

## Author

**Monte (Montgomery) Toren**  
contact@cryptix.com  
[Cryptix Security](https://github.com/Cryptix-Security)

---

*This POC demonstrates a novel approach to LLM security. Use responsibly and always test thoroughly before deploying in production environments.*
