from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.session import Base


class SemanticTimeSeries(Base):
    __tablename__ = "semantic_time_series"

    __table_args__ = (
        UniqueConstraint(
            "business_measure_id",
            "period_grain",
            "period_key",
            "dimension_signature",
            "filter_signature",
            "scope_signature",
            name="uq_semantic_time_series_point",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    business_measure_id: Mapped[int] = mapped_column(
        ForeignKey(
            "business_measures.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    period_grain: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    period_key: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    value: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=38,
            scale=10,
        ),
        nullable=False,
    )

    dimension_signature: Mapped[str] = mapped_column(
        String(64),
        default="none",
        nullable=False,
        index=True,
    )

    filter_signature: Mapped[str] = mapped_column(
        String(64),
        default="none",
        nullable=False,
        index=True,
    )

    scope_signature: Mapped[str] = mapped_column(
        String(64),
        default="enterprise",
        nullable=False,
        index=True,
    )

    source_data_source_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "data_sources.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    source_table: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    measure = relationship(
        "BusinessMeasure",
    )

    source_data_source = relationship(
        "DataSource",
    )
