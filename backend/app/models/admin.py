# Tabla `admins`: el único superusuario de la app (dueño de la API key)
from sqlmodel import Field, SQLModel


class Admin(SQLModel, table=True):
    """Single superuser for the application."""

    __tablename__ = "admins"

    id: int | None = Field(default=None, primary_key=True)   # siempre será 1
    username: str = Field(index=True, unique=True)            # "admin"
    api_key: str                                              # la clave del header X-API-Key
    is_superuser: bool = True                                 # reservado para roles futuros
