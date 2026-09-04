from sqlalchemy import (
    text,
    select,
)

from sqlalchemy.orm import (
    Session,
)

from app.core.config import (
    settings,
)

from app.models.data_source import (
    DataSource,
)

from app.services.external_database import (
    create_external_engine,
)


def get_dms_data_source(
    database: Session,
) -> DataSource:
    source = None

    # Prefer stable code.
    if settings.dms_data_source_code:
        statement = (
            select(
                DataSource
            )
            .where(
                DataSource.code
                == settings.dms_data_source_code
            )
            .where(
                DataSource.is_active
                == True
            )
        )

        source = (
            database.scalars(
                statement
            ).first()
        )

    # Fallback to configured ID.
    if (
        source is None
        and settings.dms_data_source_id
    ):
        source = database.get(
            DataSource,
            settings.dms_data_source_id,
        )

    if source is None:
        raise RuntimeError(
            "DMS datasource was not found."
        )

    if not source.is_active:
        raise RuntimeError(
            "DMS datasource is inactive."
        )

    return source


def validate_dms_table_name(
    table_name: str,
) -> str:
    # Do not let user input control table names.
    configured_table = (
        settings.dms_document_table
        or ""
    ).strip()

    if not configured_table:
        raise RuntimeError(
            "DMS_DOCUMENT_TABLE is not configured."
        )

    if table_name != configured_table:
        raise ValueError(
            "Unapproved DMS table."
        )

    return configured_table


def list_dms_documents(
    database: Session,
    limit: int = 100,
) -> list[dict]:

    source = get_dms_data_source(
        database
    )

    table_name = (
        validate_dms_table_name(
            settings.dms_document_table
        )
    )

    safe_limit = max(
        1,
        min(
            int(limit),
            500,
        ),
    )

    engine = (
        create_external_engine(
            source
        )
    )

    sql = text(
        f"""
        SELECT
            id,
            department,
            file_desc,
            filename,
            size,
            type,
            registered_by,
            date_registered
        FROM `{table_name}`
        WHERE filename IS NOT NULL
          AND TRIM(filename) <> ''
        ORDER BY date_registered DESC
        LIMIT :limit
        """
    )

    try:
        with engine.connect() as connection:
            result = connection.execute(
                sql,
                {
                    "limit":
                        safe_limit,
                },
            )

            rows = (
                result.mappings().all()
            )

        return [
            dict(row)
            for row in rows
        ]

    finally:
        engine.dispose()


def search_dms_documents(
    database: Session,
    query: str,
    department: str | None = None,
    limit: int = 20,
) -> list[dict]:

    query = (
        query
        or ""
    ).strip()

    if not query:
        raise ValueError(
            "Document search query is empty."
        )

    source = get_dms_data_source(
        database
    )

    table_name = (
        validate_dms_table_name(
            settings.dms_document_table
        )
    )

    safe_limit = max(
        1,
        min(
            int(limit),
            100,
        ),
    )

    engine = (
        create_external_engine(
            source
        )
    )

    where_parts = [
        """
        (
            LOWER(file_desc)
                LIKE LOWER(:search_term)
            OR
            LOWER(filename)
                LIKE LOWER(:search_term)
            OR
            LOWER(department)
                LIKE LOWER(:search_term)
        )
        """
    ]

    parameters = {
        "search_term":
            f"%{query}%",

        "limit":
            safe_limit,
    }

    if (
        department
        and department.strip()
    ):
        where_parts.append(
            """
            LOWER(department)
                = LOWER(:department)
            """
        )

        parameters["department"] = (
            department.strip()
        )

    where_clause = (
        " AND ".join(
            where_parts
        )
    )

    sql = text(
        f"""
        SELECT
            id,
            department,
            file_desc,
            filename,
            size,
            type,
            registered_by,
            date_registered
        FROM `{table_name}`
        WHERE
            {where_clause}
        ORDER BY
            date_registered DESC
        LIMIT :limit
        """
    )

    try:
        with engine.connect() as connection:
            result = connection.execute(
                sql,
                parameters,
            )

            rows = (
                result.mappings().all()
            )

        return [
            dict(row)
            for row in rows
        ]

    finally:
        engine.dispose()


def get_dms_document(
    database: Session,
    document_id: int,
) -> dict | None:

    source = get_dms_data_source(
        database
    )

    table_name = (
        validate_dms_table_name(
            settings.dms_document_table
        )
    )

    engine = (
        create_external_engine(
            source
        )
    )

    sql = text(
        f"""
        SELECT
            id,
            department,
            file_desc,
            filename,
            size,
            type,
            registered_by,
            date_registered
        FROM `{table_name}`
        WHERE id = :document_id
        LIMIT 1
        """
    )

    try:
        with engine.connect() as connection:
            result = connection.execute(
                sql,
                {
                    "document_id":
                        int(document_id),
                },
            )

            row = (
                result.mappings().first()
            )

        if row is None:
            return None

        return dict(
            row
        )

    finally:
        engine.dispose()