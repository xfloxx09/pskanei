from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ScrapeSettings(Base):
    __tablename__ = "scrape_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    time_window: Mapped[str] = mapped_column(String(5), default="6h", nullable=False)
    frequency_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    sources: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("id = 1", name="ck_scrape_settings_singleton"),
    )
