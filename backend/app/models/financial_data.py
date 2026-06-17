from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class CompanyMetrics(Base):
    __tablename__ = "company_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    price_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    income_statement: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    balance_sheet: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

class SECFiling(Base):
    __tablename__ = "sec_filings"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    form_type: Mapped[str] = mapped_column(String(20), nullable=False)
    filed_at: Mapped[str] = mapped_column(String(20), nullable=True)
    accession_number: Mapped[str] = mapped_column(String(50), nullable=True)
    filing_url: Mapped[str] = mapped_column(Text, nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )