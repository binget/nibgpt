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

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.session import Base


class BusinessRule(Base):
    __tablename__ = "business_rules"

    __table_args__ = (
        UniqueConstraint(
            "business_entity_id",
            "trigger_phrase",
            "metadata_column_id",
            "operator",
            "rule_value",
            name="uq_business_rule_definition",
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

    metadata_column_id: Mapped[int] = mapped_column(
        ForeignKey(
            "metadata_columns.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    trigger_phrase: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    synonyms: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    operator: Mapped[str] = mapped_column(
        String(20),
        default="=",
        nullable=False,
    )

    rule_value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
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
        back_populates="business_rules",
    )

    column = relationship(
        "MetadataColumn",
    )