import json
import re
from typing import Any

from app.models.metadata import MetadataColumn, MetadataTable


NUMERIC_TYPE_TERMS = {
    "int",
    "integer",
    "bigint",
    "smallint",
    "decimal",
    "numeric",
    "number",
    "float",
    "double",
    "real",
    "money",
}

DATE_TYPE_TERMS = {
    "date",
    "datetime",
    "timestamp",
    "time",
}

IDENTIFIER_TERMS = {
    "id",
    "identifier",
    "number",
    "code",
    "reference",
    "account",
    "name",
}

FILTER_TERMS = {
    "status",
    "state",
    "branch",
    "department",
    "currency",
    "type",
    "category",
    "date",
    "created",
    "approved",
    "assigned",
    "active",
}

MEASURE_TERMS = {
    "amount",
    "balance",
    "quantity",
    "price",
    "total",
    "cost",
    "value",
    "rate",
    "count",
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    normalized = value.lower()
    normalized = re.sub(r"[_\-]+", " ", normalized)
    normalized = re.sub(r"[^a-z0-9\s]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def parse_saved_list(value: str | None) -> list[str]:
    if not value:
        return []

    try:
        parsed = json.loads(value)

        if isinstance(parsed, list):
            return [
                str(item).strip()
                for item in parsed
                if str(item).strip()
            ]

    except (json.JSONDecodeError, TypeError):
        pass

    return [
        item.strip()
        for item in re.split(r"[,;\n]+", value)
        if item.strip()
    ]


def column_label(column: MetadataColumn) -> str:
    return (
        column.business_name
        or column.column_name.replace("_", " ").title()
    )


def is_numeric(column: MetadataColumn) -> bool:
    data_type = normalize_text(column.data_type)

    return any(
        term in data_type
        for term in NUMERIC_TYPE_TERMS
    )


def is_date(column: MetadataColumn) -> bool:
    data_type = normalize_text(column.data_type)

    return any(
        term in data_type
        for term in DATE_TYPE_TERMS
    )


def matches_terms(
    column: MetadataColumn,
    terms: set[str],
) -> bool:
    searchable = normalize_text(
        " ".join(
            filter(
                None,
                [
                    column.column_name,
                    column.business_name,
                    column.description,
                ],
            )
        )
    )

    return any(
        term in searchable
        for term in terms
    )


def determine_business_terms(
    table: MetadataTable,
) -> list[str]:
    terms = []

    terms.extend(
        parse_saved_list(table.synonyms)
    )

    if table.business_name:
        terms.append(table.business_name.lower())

    terms.append(
        table.table_name.replace("_", " ").lower()
    )

    if table.department:
        terms.append(table.department.lower())

    return list(dict.fromkeys(terms))


def determine_primary_keys(
    columns: list[MetadataColumn],
) -> list[str]:
    keys = [
        column_label(column)
        for column in columns
        if column.is_primary_key
    ]

    if keys:
        return keys

    for column in columns:
        searchable = normalize_text(
            column_label(column)
        )

        if any(
            term in searchable
            for term in IDENTIFIER_TERMS
        ):
            keys.append(column_label(column))

    return keys[:5]


def determine_filters(
    columns: list[MetadataColumn],
) -> list[str]:
    filters = []

    for column in columns:
        if (
            matches_terms(column, FILTER_TERMS)
            or is_date(column)
        ):
            filters.append(column_label(column))

    return list(dict.fromkeys(filters))[:10]


def determine_measures(
    columns: list[MetadataColumn],
) -> list[str]:
    measures = []

    for column in columns:
        if (
            is_numeric(column)
            and matches_terms(
                column,
                MEASURE_TERMS,
            )
        ):
            measures.append(column_label(column))

    return list(dict.fromkeys(measures))[:10]


def determine_related_entities(
    columns: list[MetadataColumn],
) -> list[str]:
    entities = []

    for column in columns:
        name = normalize_text(column.column_name)

        if name.endswith(" id"):
            entity = name.removesuffix(" id").strip()

            if entity:
                entities.append(entity.title())

        elif name.endswith(" code"):
            entity = name.removesuffix(" code").strip()

            if entity:
                entities.append(entity.title())

    return list(dict.fromkeys(entities))[:10]


def create_common_questions(
    table_name: str,
    filters: list[str],
    measures: list[str],
) -> list[str]:
    questions = [
        f"Show all {table_name.lower()}",
        f"How many {table_name.lower()} records are available?",
    ]

    for filter_name in filters[:3]:
        questions.append(
            f"Show {table_name.lower()} by {filter_name.lower()}"
        )

    for measure_name in measures[:3]:
        questions.append(
            f"Show total {measure_name.lower()} for {table_name.lower()}"
        )

    return list(dict.fromkeys(questions))[:8]


def build_knowledge_profile(
    table: MetadataTable,
) -> dict[str, Any]:
    active_columns = [
        column
        for column in table.columns
        if (
            column.is_discovered
            and column.is_enabled
        )
    ]

    business_name = (
        table.business_name
        or table.table_name.replace("_", " ").title()
    )

    business_terms = determine_business_terms(table)
    primary_keys = determine_primary_keys(active_columns)
    filters = determine_filters(active_columns)
    measures = determine_measures(active_columns)
    related_entities = determine_related_entities(
        active_columns
    )

    questions = create_common_questions(
        table_name=business_name,
        filters=filters,
        measures=measures,
    )

    purpose = (
        table.business_purpose
        or table.description
        or (
            f"Provides business information related to "
            f"{business_name.lower()} for reporting, "
            f"analysis and operational decision support."
        )
    )

    reasons = [
        f"Analysed {len(active_columns)} enabled column(s).",
    ]

    if primary_keys:
        reasons.append(
            f"Identified {len(primary_keys)} business key candidate(s)."
        )

    if filters:
        reasons.append(
            f"Identified {len(filters)} commonly filterable field(s)."
        )

    if measures:
        reasons.append(
            f"Identified {len(measures)} measurable numeric field(s)."
        )

    if related_entities:
        reasons.append(
            f"Identified {len(related_entities)} related business entity candidate(s)."
        )

    completeness = sum(
        [
            bool(table.business_name),
            bool(table.description),
            bool(business_terms),
            bool(primary_keys),
            bool(filters),
            bool(measures),
        ]
    )

    confidence = min(
        98,
        58 + (completeness * 6),
    )

    return {
        "table_id": table.id,
        "technical_name": table.table_name,
        "business_name": business_name,
        "business_purpose": purpose,
        "business_terms": business_terms,
        "common_questions": questions,
        "common_filters": filters,
        "common_measures": measures,
        "primary_business_keys": primary_keys,
        "related_entities": related_entities,
        "ai_notes": (
            "Use only enabled, discovered and AI-approved columns. "
            "Apply governance, classification and row-limit rules "
            "before compiling or executing a query."
        ),
        "confidence": confidence,
        "reasons": reasons,
    }
