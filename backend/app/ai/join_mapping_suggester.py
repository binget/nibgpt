import re

from app.models.metadata import (
    MetadataColumn,
)


def normalize_text(
    value: str | None,
) -> str:
    if not value:
        return ""

    normalized = value.lower()

    normalized = re.sub(
        r"[_\-]+",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"[^a-z0-9\s]+",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip()


def normalize_data_type(
    value: str | None,
) -> str:
    normalized = normalize_text(value)

    aliases = {
        "integer": "int",
        "bigint": "int",
        "smallint": "int",
        "number": "numeric",
        "decimal": "numeric",
        "double precision": "numeric",
        "character varying": "string",
        "varchar": "string",
        "nvarchar": "string",
        "char": "string",
        "text": "string",
        "timestamp without time zone": "datetime",
        "timestamp with time zone": "datetime",
    }

    for key, target in aliases.items():
        if key in normalized:
            return target

    return normalized


def names_are_similar(
    source: MetadataColumn,
    target: MetadataColumn,
) -> bool:
    source_name = normalize_text(
        source.business_name
        or source.column_name
    )

    target_name = normalize_text(
        target.business_name
        or target.column_name
    )

    if source_name == target_name:
        return True

    source_compact = source_name.replace(
        " ",
        "",
    )

    target_compact = target_name.replace(
        " ",
        "",
    )

    if source_compact == target_compact:
        return True

    source_without_id = re.sub(
        r"\b(id|identifier|number|code)\b",
        "",
        source_name,
    ).strip()

    target_without_id = re.sub(
        r"\b(id|identifier|number|code)\b",
        "",
        target_name,
    ).strip()

    return (
        bool(source_without_id)
        and source_without_id
        == target_without_id
    )


def suggest_join_mapping(
    relationship_id: int,
    source_columns: list[MetadataColumn],
    target_columns: list[MetadataColumn],
) -> dict | None:
    best_match = None
    best_score = -1
    best_reasons: list[str] = []

    for source_column in source_columns:
        for target_column in target_columns:
            score = 0
            reasons: list[str] = []

            source_type = normalize_data_type(
                source_column.data_type
            )

            target_type = normalize_data_type(
                target_column.data_type
            )

            if source_type == target_type:
                score += 30
                reasons.append(
                    "The column data types are compatible."
                )

            elif (
                source_type in {
                    "int",
                    "numeric",
                }
                and target_type in {
                    "int",
                    "numeric",
                }
            ):
                score += 22
                reasons.append(
                    "The columns use compatible numeric types."
                )

            else:
                continue

            if names_are_similar(
                source_column,
                target_column,
            ):
                score += 50
                reasons.append(
                    "The column names or business names match."
                )

            if source_column.is_primary_key:
                score += 15
                reasons.append(
                    "The source column is a primary key."
                )

            if target_column.is_primary_key:
                score += 15
                reasons.append(
                    "The target column is a primary key."
                )

            source_name = normalize_text(
                source_column.column_name
            )

            target_name = normalize_text(
                target_column.column_name
            )

            if source_name.endswith(
                " id"
            ) or target_name.endswith(
                " id"
            ):
                score += 8
                reasons.append(
                    "One or both columns appear to be identifiers."
                )

            if score > best_score:
                best_score = score
                best_match = (
                    source_column,
                    target_column,
                )
                best_reasons = reasons

    if best_match is None:
        return None

    source_column, target_column = (
        best_match
    )

    confidence = min(
        98,
        45 + best_score,
    )

    return {
        "relationship_id": relationship_id,
        "source_metadata_table_id": (
            source_column.metadata_table_id
        ),
        "source_metadata_column_id": (
            source_column.id
        ),
        "target_metadata_table_id": (
            target_column.metadata_table_id
        ),
        "target_metadata_column_id": (
            target_column.id
        ),
        "join_type": "inner",
        "confidence": confidence,
        "description": (
            f"Joins {source_column.column_name} "
            f"to {target_column.column_name} "
            f"for the selected semantic relationship."
        ),
        "reasons": best_reasons,
    }
