"""Optional HTTP Basic Auth gate.

If APP_USER and APP_PASSWORD are set, every request must carry matching Basic Auth
credentials. If they are unset (local dev), the app is open. Kept as a middleware
so it also covers the static frontend, not just the API routes.
"""

from __future__ import annotations

import base64
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from . import config

_REALM = 'Basic realm="Kensai Product Intelligence"'


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not config.auth_enabled():
            return await call_next(request)

        header = request.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                user, _, pw = base64.b64decode(header[6:]).decode().partition(":")
                if (secrets.compare_digest(user, config.APP_USER)
                        and secrets.compare_digest(pw, config.APP_PASSWORD)):
                    return await call_next(request)
            except Exception:  # noqa: BLE001 - malformed header -> treat as unauthorised
                pass

        return Response(status_code=401, headers={"WWW-Authenticate": _REALM})
