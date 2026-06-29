from sqlmodel import Field, SQLModel


class Admin(SQLModel, table=True):
    """Single superuser for the application."""

    __tablename__ = "admins"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    api_key: str
    is_superuser: bool = True