from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session, selectinload

from app.models.data_source import DataSource
from app.models.metadata import (
    MetadataColumn,
    MetadataTable,
)
from app.services.external_database import (
    create_external_engine,
)


@dataclass
class ScanResult:
    schemas_scanned: int = 0
    tables_discovered: int = 0
    views_discovered: int = 0
    columns_discovered: int = 0

    new_tables: int = 0
    updated_tables: int = 0
    removed_tables: int = 0

    new_columns: int = 0
    updated_columns: int = 0
    removed_columns: int = 0


SYSTEM_SCHEMAS = {
    "information_schema",
    "pg_catalog",
    "pg_toast",
    "mysql",
    "performance_schema",
    "sys",
}


def normalize_default(
    value: object,
) -> str | None:
    if value is None:
        return None

    return str(value)[:1000]


def normalize_schema(
    schema_name: str | None,
) -> str:
    return schema_name or ""


def discover_schemas(
    source: DataSource,
    inspector,
) -> list[str | None]:
    database_type = source.database_type.lower()

    if database_type == "mysql":
        return [source.database_name]

    if database_type == "oracle":
        return [source.username.upper()]

    schemas = inspector.get_schema_names()

    filtered_schemas = [
        schema
        for schema in schemas
        if schema.lower() not in SYSTEM_SCHEMAS
    ]

    return filtered_schemas or ["public"]


def scan_data_source_metadata(
    database: Session,
    source: DataSource,
) -> ScanResult:
    engine = create_external_engine(source)
    result = ScanResult()
    scan_time = datetime.utcnow()

    try:
        inspector = inspect(engine)

        schemas = discover_schemas(
            source,
            inspector,
        )

        result.schemas_scanned = len(schemas)

        existing_statement = (
            select(MetadataTable)
            .options(
                selectinload(
                    MetadataTable.columns
                )
            )
            .where(
                MetadataTable.data_source_id
                == source.id
            )
        )

        existing_tables = list(
            database.scalars(
                existing_statement
            ).all()
        )

        existing_table_map = {
            (
                normalize_schema(
                    table.schema_name
                ),
                table.table_name,
            ): table
            for table in existing_tables
        }

        seen_table_keys: set[
            tuple[str, str]
        ] = set()

        seen_column_ids: set[int] = set()

        for schema_name in schemas:
            table_names = inspector.get_table_names(
                schema=schema_name
            )

            view_names = inspector.get_view_names(
                schema=schema_name
            )

            result.tables_discovered += len(
                table_names
            )

            result.views_discovered += len(
                view_names
            )

            objects = [
                (name, "table")
                for name in table_names
            ]

            objects.extend(
                (name, "view")
                for name in view_names
            )

            for object_name, object_type in objects:
                table_key = (
                    normalize_schema(
                        schema_name
                    ),
                    object_name,
                )

                seen_table_keys.add(table_key)

                metadata_table = (
                    existing_table_map.get(
                        table_key
                    )
                )

                if metadata_table is None:
                    metadata_table = MetadataTable(
                        data_source_id=source.id,
                        schema_name=schema_name,
                        table_name=object_name,
                        object_type=object_type,
                        is_discovered=True,
                        last_seen_at=scan_time,
                        discovered_at=scan_time,
                    )

                    database.add(metadata_table)
                    database.flush()

                    existing_table_map[
                        table_key
                    ] = metadata_table

                    result.new_tables += 1

                else:
                    # Update technical metadata only.
                    # Business Dictionary fields remain untouched.
                    metadata_table.object_type = (
                        object_type
                    )
                    metadata_table.is_discovered = (
                        True
                    )
                    metadata_table.last_seen_at = (
                        scan_time
                    )

                    result.updated_tables += 1

                primary_key = (
                    inspector.get_pk_constraint(
                        object_name,
                        schema=schema_name,
                    )
                    or {}
                )

                primary_key_columns = set(
                    primary_key.get(
                        "constrained_columns"
                    )
                    or []
                )

                discovered_columns = (
                    inspector.get_columns(
                        object_name,
                        schema=schema_name,
                    )
                )

                existing_column_map = {
                    column.column_name: column
                    for column
                    in metadata_table.columns
                }

                seen_column_names: set[str] = (
                    set()
                )

                for position, column_info in enumerate(
                    discovered_columns,
                    start=1,
                ):
                    column_name = str(
                        column_info["name"]
                    )

                    seen_column_names.add(
                        column_name
                    )

                    metadata_column = (
                        existing_column_map.get(
                            column_name
                        )
                    )

                    if metadata_column is None:
                        metadata_column = (
                            MetadataColumn(
                                metadata_table_id=(
                                    metadata_table.id
                                ),
                                column_name=(
                                    column_name
                                ),
                                data_type=str(
                                    column_info.get(
                                        "type",
                                        "UNKNOWN",
                                    )
                                ),
                                ordinal_position=(
                                    position
                                ),
                                is_nullable=bool(
                                    column_info.get(
                                        "nullable",
                                        True,
                                    )
                                ),
                                is_primary_key=(
                                    column_name
                                    in primary_key_columns
                                ),
                                default_value=(
                                    normalize_default(
                                        column_info.get(
                                            "default"
                                        )
                                    )
                                ),
                                is_discovered=True,
                                last_seen_at=(
                                    scan_time
                                ),
                            )
                        )

                        database.add(
                            metadata_column
                        )
                        database.flush()

                        existing_column_map[
                            column_name
                        ] = metadata_column

                        result.new_columns += 1

                    else:
                        # Refresh only technical properties.
                        metadata_column.data_type = str(
                            column_info.get(
                                "type",
                                "UNKNOWN",
                            )
                        )

                        metadata_column.ordinal_position = (
                            position
                        )

                        metadata_column.is_nullable = (
                            bool(
                                column_info.get(
                                    "nullable",
                                    True,
                                )
                            )
                        )

                        metadata_column.is_primary_key = (
                            column_name
                            in primary_key_columns
                        )

                        metadata_column.default_value = (
                            normalize_default(
                                column_info.get(
                                    "default"
                                )
                            )
                        )

                        metadata_column.is_discovered = (
                            True
                        )

                        metadata_column.last_seen_at = (
                            scan_time
                        )

                        result.updated_columns += 1

                    seen_column_ids.add(
                        metadata_column.id
                    )

                # Mark columns removed from this table.
                for existing_column in (
                    metadata_table.columns
                ):
                    if (
                        existing_column.column_name
                        not in seen_column_names
                    ):
                        if (
                            existing_column.is_discovered
                        ):
                            result.removed_columns += 1

                        existing_column.is_discovered = (
                            False
                        )

        # Mark tables no longer found in the source.
        for table_key, table in (
            existing_table_map.items()
        ):
            if table_key not in seen_table_keys:
                if table.is_discovered:
                    result.removed_tables += 1

                table.is_discovered = False

                for column in table.columns:
                    if column.is_discovered:
                        result.removed_columns += 1

                    column.is_discovered = False

        result.columns_discovered = (
            result.new_columns
            + result.updated_columns
        )

        database.commit()

        return result

    except Exception:
        database.rollback()
        raise

    finally:
        engine.dispose()