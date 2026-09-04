from app.database.session import (
    Base,
    engine,
)

from app.models.document_index import (
    DocumentIndex,
)

from app.models.document_chunk import (
    DocumentChunk,
)


def main() -> None:

    print(
        "Creating NIBGPT document cache tables..."
    )

    Base.metadata.create_all(
        bind=engine,
        tables=[
            DocumentIndex.__table__,
            DocumentChunk.__table__,
        ],
    )

    print(
        "Document cache tables created successfully."
    )


if __name__ == "__main__":
    main()
