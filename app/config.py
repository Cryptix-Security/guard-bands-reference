import json
import os
import sys

from dotenv import load_dotenv
from guardbands import GuardBandKey

from app.secrets_provider import build_secret_provider

load_dotenv()


class Settings:
    # Core
    SECRET_KEY: bytes
    KEY_ID: str
    GUARD_BAND_KEYS: dict[str, GuardBandKey]
    ANTHROPIC_API_KEY: str
    DEBUG: bool
    GUARD_BAND_TTL_SECONDS: int
    ALLOWED_ORIGINS: list[str]
    REPLAY_PROTECTION_ENABLED: bool
    REPLAY_LEDGER_BACKEND: str
    REPLAY_LEDGER_PATH: str
    REPLAY_WINDOW_SECONDS: int

    # Audit — PostgreSQL
    LOG_POSTGRES_DSN: str

    # Audit — Splunk HEC
    LOG_SPLUNK_HEC_URL: str
    LOG_SPLUNK_HEC_TOKEN: str
    LOG_SPLUNK_INDEX: str
    LOG_SPLUNK_SOURCE: str
    LOG_SPLUNK_SSL_VERIFY: bool
    LLM_MODEL: str
    LLM_MAX_OUTPUT_TOKENS: int
    COST_GUARD_ENABLED: bool
    COST_GUARD_THRESHOLD_USD: float
    COST_GUARD_INPUT_USD_PER_MTOK: float
    COST_GUARD_OUTPUT_USD_PER_MTOK: float

    def __init__(self) -> None:
        # Secret-bearing settings resolve through the configured provider
        # (env by default; aws or vault when SECRETS_BACKEND is set).
        self._secrets = build_secret_provider()

        raw_key = self._secrets.get_secret("SECRET_KEY", "") or ""
        if not raw_key:
            sys.exit(
                "FATAL: SECRET_KEY is not set. Provide it via the environment "
                "(or SECRETS_BACKEND=aws|vault). Generate one with: "
                'python3 -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        self.SECRET_KEY = raw_key.encode("utf-8")
        self.KEY_ID = os.getenv("KEY_ID", "key001")
        self.GUARD_BAND_KEYS = self._load_guard_band_keys(raw_key)

        self.ANTHROPIC_API_KEY = self._secrets.get_secret("ANTHROPIC_API_KEY", "") or ""
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        # Lifetime stamped into each wrapped band (authenticated iat/exp). Bands
        # verify as expired past this window, independent of the replay ledger.
        self.GUARD_BAND_TTL_SECONDS = int(os.getenv("GUARD_BAND_TTL_SECONDS", "900"))
        self.REPLAY_PROTECTION_ENABLED = (
            os.getenv("REPLAY_PROTECTION_ENABLED", "false").lower() == "true"
        )
        self.REPLAY_LEDGER_BACKEND = os.getenv("REPLAY_LEDGER_BACKEND", "memory")
        self.REPLAY_LEDGER_PATH = os.getenv("REPLAY_LEDGER_PATH", "data/replay-ledger.sqlite3")
        self.REPLAY_WINDOW_SECONDS = int(os.getenv("REPLAY_WINDOW_SECONDS", "900"))

        origins_raw = os.getenv("ALLOWED_ORIGINS", "")
        self.ALLOWED_ORIGINS = [o.strip() for o in origins_raw.split(",") if o.strip()]

        # Logging sinks (optional — omit to disable). DSN and HEC token are
        # secret-bearing, so they resolve through the secret provider.
        self.LOG_POSTGRES_DSN = self._secrets.get_secret("LOG_POSTGRES_DSN", "") or ""

        self.LOG_SPLUNK_HEC_URL = os.getenv("LOG_SPLUNK_HEC_URL", "")
        self.LOG_SPLUNK_HEC_TOKEN = self._secrets.get_secret("LOG_SPLUNK_HEC_TOKEN", "") or ""
        self.LOG_SPLUNK_INDEX = os.getenv("LOG_SPLUNK_INDEX", "guard_bands")
        self.LOG_SPLUNK_SOURCE = os.getenv("LOG_SPLUNK_SOURCE", "guard-bands-api")
        self.LOG_SPLUNK_SSL_VERIFY = os.getenv("LOG_SPLUNK_SSL_VERIFY", "true").lower() == "true"

        self.LLM_MODEL = os.getenv("LLM_MODEL", "claude-3-5-haiku-20241022")
        self.LLM_MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "2048"))
        self.COST_GUARD_ENABLED = os.getenv("COST_GUARD_ENABLED", "true").lower() == "true"
        self.COST_GUARD_THRESHOLD_USD = float(os.getenv("COST_GUARD_THRESHOLD_USD", "1.00"))
        self.COST_GUARD_INPUT_USD_PER_MTOK = float(
            os.getenv("COST_GUARD_INPUT_USD_PER_MTOK", "1.00")
        )
        self.COST_GUARD_OUTPUT_USD_PER_MTOK = float(
            os.getenv("COST_GUARD_OUTPUT_USD_PER_MTOK", "5.00")
        )

        # SSO — set by oauth2-proxy headers; disabled by default for local dev
        # oauth2-proxy --pass-user-headers=true sets X-Forwarded-User / X-Forwarded-Email
        # (--set-xauthrequest is for nginx auth_request mode only — response headers, not upstream)
        self.SSO_ENABLED = os.getenv("SSO_ENABLED", "false").lower() == "true"
        self.SSO_HEADER_USER = os.getenv("SSO_HEADER_USER", "X-Forwarded-User")
        self.SSO_HEADER_EMAIL = os.getenv("SSO_HEADER_EMAIL", "X-Forwarded-Email")

    def _load_guard_band_keys(self, fallback_key: str) -> dict[str, GuardBandKey]:
        raw_keys = self._secrets.get_secret("GUARD_BAND_KEYS", "") or ""
        if not raw_keys:
            return {self.KEY_ID: fallback_key.encode("utf-8")}

        try:
            parsed = json.loads(raw_keys)
        except json.JSONDecodeError as e:
            sys.exit(f"FATAL: GUARD_BAND_KEYS must be a JSON object: {e}")

        if not isinstance(parsed, dict) or not parsed:
            sys.exit("FATAL: GUARD_BAND_KEYS must be a non-empty JSON object")

        keys: dict[str, GuardBandKey] = {}
        for key_id, key_value in parsed.items():
            if not isinstance(key_id, str) or not isinstance(key_value, str):
                sys.exit("FATAL: GUARD_BAND_KEYS must map string key ids to string secrets")
            keys[key_id] = key_value.encode("utf-8")
        return keys


settings = Settings()
