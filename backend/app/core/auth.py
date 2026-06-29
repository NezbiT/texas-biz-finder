from fastapi import Header, HTTPException, status

from backend.app.config import settings


def require_admin(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Validate the single superuser API key."""
    if x_api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key",
        )
    return x_api_key