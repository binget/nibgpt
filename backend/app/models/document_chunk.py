from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.session import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    __table_args__ = (
        Index(
            "ix_document_chunks_document_order",
            "document_index_id",
            "chunk_order",
        ),
        Index(
            "ix_document_chunks_section",
            "section_number",
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

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    start_page: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    end_page: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    section_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    section_title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    parent_section_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    parent_section_title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    extraction_method: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    chunk_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    document = relationship(
        "DocumentIndex",
        back_populates="chunks",
    )