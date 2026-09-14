from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class DocumentLearning(Base):
    __tablename__ = "document_learning"

    __table_args__ = (
        UniqueConstraint(
            "document_index_id",
            "learning_type",
            "learning_key",
            name="uq_document_learning_key",
        ),
        Index(
            "ix_document_learning_lookup",
            "learning_type",
            "learning_key",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    document_index_id: Mapped[int] = mapped_column(
        ForeignKey(
            "document_index.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    learning_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    learning_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    learning_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )

    source_page: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    source_section: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    learned_by: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="automatic",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
