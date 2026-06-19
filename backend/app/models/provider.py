from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
