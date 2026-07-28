# Autenticación mínima de la API: una sola API key de admin en el header X-API-Key
from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from backend.app.config import settings

_INSECURE_DEFAULTS = frozenset(
    {
        "",
        "admin-dev-key-change-me",
        "changeme",
        "secret",
        "password",
    }
)


def require_admin(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Dependencia de FastAPI: valida la API key del superusuario único.

    Comparación timing-safe. En production/staging rechaza keys inseguras por defecto.
    """
    expected = (settings.admin_api_key or "").strip()
    if not expected or expected in _INSECURE_DEFAULTS:
        if settings.is_production:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ADMIN_API_KEY is missing or uses an insecure default. Rotate before production.",
            )
        # Dev: allow default key for local tests only

    if not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key
