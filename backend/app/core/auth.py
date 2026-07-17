# Autenticación mínima de la API: una sola API key de admin en el header X-API-Key
from fastapi import Header, HTTPException, status

from backend.app.config import settings


def require_admin(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Dependencia de FastAPI: valida la API key del superusuario único.

    `...` = header obligatorio; si falta o no coincide → 401."""
    if x_api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key",
        )
    return x_api_key   # se devuelve por si algún endpoint quiere registrarla
