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


class BusinessCapability(Base):
    __tablename__ = "business_capabilities"

    __table_args__ = (
        UniqueConstraint(
            "domain_id",
            "name",
            name="uq_business_capability_domain_name",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    domain_id: Mapped[int] = mapped_column(
        ForeignKey(
            "business_domains.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    parent_capability_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "business_capabilities.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    business_owner: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    capability_type: Mapped[str] = mapped_column(
        String(40),
        default="operational",
        nullable=False,
    )

    maturity_level: Mapped[str] = mapped_column(
        String(40),
        default="developing",
        nullable=False,
    )

    approval_status: Mapped[str] = mapped_column(
        String(30),
        default="draft",
        nullable=False,
    )

    confidence: Mapped[int] = mapped_column(
        Integer,
        default=0,
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

    domain = relationship(
        "BusinessDomain",
    )

    parent_capability = relationship(
        "BusinessCapability",
        remote_side=[id],
        back_populates="child_capabilities",
    )

    child_capabilities: Mapped[
        list["BusinessCapability"]
    ] = relationship(
        back_populates="parent_capability",
    )

    entity_mappings: Mapped[
        list["BusinessCapabilityEntityMap"]
    ] = relationship(
        back_populates="capability",
        cascade="all, delete-orphan",
    )


class BusinessCapabilityEntityMap(Base):
    __tablename__ = "business_capability_entity_maps"

    __table_args__ = (
        UniqueConstraint(
            "capability_id",
            "business_entity_id",
            name="uq_capability_entity_mapping",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    capability_id: Mapped[int] = mapped_column(
        ForeignKey(
            "business_capabilities.id",
            ondelete="CASCADE",
        ),
        nullable=False,
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

    mapping_role: Mapped[str] = mapped_column(
        String(40),
        default="primary",
        nullable=False,
    )

    confidence: Mapped[int] = mapped_column(
        Integer,
        default=100,
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

    capability: Mapped["BusinessCapability"] = relationship(
        back_populates="entity_mappings",
    )

    business_entity = relationship(
        "BusinessEntity",
    )
