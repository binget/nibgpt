from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class MetadataTable(Base):
    __tablename__ = "metadata_tables"

    __table_args__ = (
        UniqueConstraint(
            "data_source_id",
            "schema_name",
            "table_name",
            name="uq_metadata_table",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    data_source_id: Mapped[int] = mapped_column(
        ForeignKey(
            "data_sources.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    schema_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    table_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    object_type: Mapped[str] = mapped_column(
        String(30),
        default="table",
        nullable=False,
    )

    business_name: Mapped[str | None] = mapped_column(
        String(250),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    data_owner: Mapped[str | None] = mapped_column(
    String(150),
    nullable=True,
    )

    department: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    classification: Mapped[str] = mapped_column(
        String(30),
        default="internal",
        nullable=False,
    )

    ai_access_allowed: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    synonyms: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


    suggested_questions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    business_purpose: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
    )

    business_terms: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    common_filters: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    common_measures: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    primary_business_keys: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    related_entities: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ai_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    knowledge_status: Mapped[str] = mapped_column(
        String(30),
        default="not_generated",
        nullable=False,
    )

    definition_status: Mapped[str] = mapped_column(
        String(30),
        default="not_generated",
        nullable=False,
    )

    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_discovered: Mapped[bool] = mapped_column(
    Boolean,
    default=True,
    nullable=False,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    discovered_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    columns: Mapped[list["MetadataColumn"]] = relationship(
        back_populates="table",
        cascade="all, delete-orphan",
        order_by="MetadataColumn.ordinal_position",
    )


class MetadataColumn(Base):
    __tablename__ = "metadata_columns"

    __table_args__ = (
        UniqueConstraint(
            "metadata_table_id",
            "column_name",
            name="uq_metadata_column",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    metadata_table_id: Mapped[int] = mapped_column(
        ForeignKey(
            "metadata_tables.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    column_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    data_type: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    ordinal_position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    is_nullable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_primary_key: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    default_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    business_name: Mapped[str | None] = mapped_column(
        String(250),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    classification: Mapped[str] = mapped_column(
    String(30),
    default="internal",
    nullable=False,
    )

    ai_access_allowed: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    synonyms: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
    )

    definition_status: Mapped[str] = mapped_column(
        String(30),
        default="not_generated",
        nullable=False,
    )

    is_sensitive: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_discovered: Mapped[bool] = mapped_column(
    Boolean,
    default=True,
    nullable=False,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    table: Mapped["MetadataTable"] = relationship(
        back_populates="columns"
    )
