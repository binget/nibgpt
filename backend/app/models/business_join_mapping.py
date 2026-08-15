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


class BusinessRelationshipJoinMapping(Base):
    __tablename__ = "business_relationship_join_mappings"

    __table_args__ = (
        UniqueConstraint(
            "relationship_id",
            "source_metadata_table_id",
            "source_metadata_column_id",
            "target_metadata_table_id",
            "target_metadata_column_id",
            name="uq_business_relationship_join_mapping",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    relationship_id: Mapped[int] = mapped_column(
        ForeignKey(
            "business_entity_relationships.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    source_metadata_table_id: Mapped[int] = mapped_column(
        ForeignKey(
            "metadata_tables.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    source_metadata_column_id: Mapped[int] = mapped_column(
        ForeignKey(
            "metadata_columns.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    target_metadata_table_id: Mapped[int] = mapped_column(
        ForeignKey(
            "metadata_tables.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    target_metadata_column_id: Mapped[int] = mapped_column(
        ForeignKey(
            "metadata_columns.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    join_type: Mapped[str] = mapped_column(
        String(20),
        default="inner",
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

    business_relationship = relationship(
    "BusinessEntityRelationship"
    )

    source_table = relationship(
        "MetadataTable",
        foreign_keys=[
            source_metadata_table_id
        ],
    )

    source_column = relationship(
        "MetadataColumn",
        foreign_keys=[
            source_metadata_column_id
        ],
    )

    target_table = relationship(
        "MetadataTable",
        foreign_keys=[
            target_metadata_table_id
        ],
    )

    target_column = relationship(
        "MetadataColumn",
        foreign_keys=[
            target_metadata_column_id
        ],
    )
