from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

# Paths that bypass SSO enforcement (proxy health probes, public status)
_PUBLIC_PATHS = {"/health", "/"}


class SSOHeaderMiddleware(BaseHTTPMiddleware):
    """
    Reads user identity injected by oauth2-proxy:
      X-Auth-Request-User  → request.state.user_id    (preferred_username / sub)
      X-Auth-Request-Email → request.state.user_email

    When SSO_ENABLED=true, rejects any request missing the identity header
    that didn't come through the proxy — defense-in-depth against direct
    access to port 8000.  Set SSO_ENABLED=false for local dev without the
    full Docker stack.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        user_id = request.headers.get(settings.SSO_HEADER_USER)
        user_email = request.headers.get(settings.SSO_HEADER_EMAIL)

        request.state.user_id = user_id
        request.state.user_email = user_email

        if settings.SSO_ENABLED and not user_id and request.url.path not in _PUBLIC_PATHS:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required. Send a valid Bearer token."},
            )

        return await call_next(request)
