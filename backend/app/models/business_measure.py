from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.session import Base


class BusinessMeasure(Base):
    __tablename__ = "business_measures"

    __table_args__ = (
        UniqueConstraint(
            "business_entity_id",
            "name",
            name="uq_business_measure_entity_name",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    business_entity_id: Mapped[int] = mapped_column(
        ForeignKey(
            "business_entities.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    metadata_column_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "metadata_columns.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    aggregation_function: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    
    temporal_behavior: Mapped[str] = mapped_column(
        String(30),
        default="event",
        nullable=False,
    )

    time_axis_column_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "metadata_columns.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    period_selection: Mapped[str] = mapped_column(
        String(30),
        default="all_rows",
        nullable=False,
    )

    historical_source_table_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "metadata_tables.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    historical_value_column_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "metadata_columns.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    
    temporal_behavior: Mapped[str] = mapped_column(
        String(30),
        default="event",
        nullable=False,
    )

    time_axis_column_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "metadata_columns.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    period_selection: Mapped[str] = mapped_column(
        String(30),
        default="all_rows",
        nullable=False,
    )

    historical_source_table_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "metadata_tables.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    trigger_phrases: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    synonyms: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    confidence: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
    )

    approval_status: Mapped[str] = mapped_column(
        String(30),
        default="draft",
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    entity = relationship(
        "BusinessEntity",
    )

    column = relationship(
        "MetadataColumn",
        foreign_keys=[metadata_column_id],
    )

    time_axis_column = relationship(
        "MetadataColumn",
        foreign_keys=[time_axis_column_id],
    )

    historical_value_column = relationship(
        "MetadataColumn",
        foreign_keys=[historical_value_column_id],
    )

    historical_source_table = relationship(
        "MetadataTable",
        foreign_keys=[historical_source_table_id],
    )
    
    time_axis_column = relationship(
        "MetadataColumn",
        foreign_keys=[time_axis_column_id],
    )

    historical_source_table = relationship(
        "MetadataTable",
        foreign_keys=[historical_source_table_id],
    )