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


class BusinessDomain(Base):
    __tablename__ = "business_domains"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    department: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    owner: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
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

    entities: Mapped[list["BusinessEntity"]] = relationship(
        back_populates="domain",
        cascade="all, delete-orphan",
    )


class BusinessEntity(Base):
    __tablename__ = "business_entities"

    __table_args__ = (
        UniqueConstraint(
            "domain_id",
            "name",
            name="uq_business_entity_domain_name",
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

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    synonyms: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    business_owner: Mapped[str | None] = mapped_column(
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

    domain: Mapped["BusinessDomain"] = relationship(
        back_populates="entities"
    )

    table_mappings: Mapped[list["BusinessEntityTableMap"]] = relationship(
        back_populates="entity",
        cascade="all, delete-orphan",
    )

    business_rules: Mapped[list["BusinessRule"]] = relationship(
        back_populates="entity",
        cascade="all, delete-orphan",
    )


class BusinessEntityTableMap(Base):
    __tablename__ = "business_entity_table_maps"

    __table_args__ = (
        UniqueConstraint(
            "business_entity_id",
            "metadata_table_id",
            name="uq_entity_table_mapping",
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

    metadata_table_id: Mapped[int] = mapped_column(
        ForeignKey(
            "metadata_tables.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    mapping_type: Mapped[str] = mapped_column(
        String(30),
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

    entity: Mapped["BusinessEntity"] = relationship(
        back_populates="table_mappings"
    )
