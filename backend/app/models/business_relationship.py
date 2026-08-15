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


class BusinessEntityRelationship(Base):
    __tablename__ = "business_entity_relationships"

    __table_args__ = (
        UniqueConstraint(
            "source_entity_id",
            "target_entity_id",
            "relationship_name",
            name="uq_business_entity_relationship",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    source_entity_id: Mapped[int] = mapped_column(
        ForeignKey(
            "business_entities.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    target_entity_id: Mapped[int] = mapped_column(
        ForeignKey(
            "business_entities.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    relationship_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    inverse_relationship_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    relationship_type: Mapped[str] = mapped_column(
        String(40),
        default="business",
        nullable=False,
    )

    cardinality: Mapped[str] = mapped_column(
        String(40),
        default="many_to_one",
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    confidence: Mapped[int] = mapped_column(
        Integer,
        default=0,
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

    source_entity = relationship(
        "BusinessEntity",
        foreign_keys=[source_entity_id],
    )

    target_entity = relationship(
        "BusinessEntity",
        foreign_keys=[target_entity_id],
    )
