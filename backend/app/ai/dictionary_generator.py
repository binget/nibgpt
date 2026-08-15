import re
from dataclasses import dataclass

from app.models.metadata import MetadataColumn, MetadataTable


WORD_REPLACEMENTS = {
    "acct": "account",
    "acc": "account",
    "amt": "amount",
    "bal": "balance",
    "cust": "customer",
    "dept": "department",
    "desc": "description",
    "dt": "date",
    "emp": "employee",
    "exp": "expiry",
    "fcy": "foreign currency",
    "id": "identifier",
    "no": "number",
    "qty": "quantity",
    "req": "request",
    "txn": "transaction",
    "veh": "vehicle",
}


SENSITIVE_TERMS = {
    "account number",
    "customer number",
    "customer name",
    "email",
    "mobile",
    "national identifier",
    "passport",
    "password",
    "phone",
    "salary",
    "tin",
}


DATE_TERMS = {
    "created date",
    "date created",
    "expiry date",
    "registration date",
    "request date",
    "start date",
    "end date",
    "transaction date",
}


@dataclass
class GeneratedColumn:
    column_id: int
    technical_name: str
    business_name: str
    description: str
    synonyms: list[str]
    classification: str
    is_sensitive: bool


def normalize_identifier(value: str) -> list[str]:
    value = re.sub(
        r"([a-z0-9])([A-Z])",
        r"\1 \2",
        value,
    )

    value = re.sub(
        r"[^a-zA-Z0-9]+",
        " ",
        value,
    )

    words = []

    for word in value.lower().split():
        replacement = WORD_REPLACEMENTS.get(
            word,
            word,
        )

        words.extend(replacement.split())

    return words


def title_from_identifier(value: str) -> str:
    words = normalize_identifier(value)

    return " ".join(words).title()


def singularize(value: str) -> str:
    lowered = value.lower()

    if lowered.endswith("ies"):
        return value[:-3] + "y"

    if lowered.endswith("sses"):
        return value

    if lowered.endswith("s") and not lowered.endswith("ss"):
        return value[:-1]

    return value


def create_synonyms(
    technical_name: str,
    business_name: str,
) -> list[str]:
    technical_words = " ".join(
        normalize_identifier(technical_name)
    )

    business_lower = business_name.lower()

    candidates = [
        technical_name.lower(),
        technical_words,
        business_lower,
        singularize(business_lower),
    ]

    return list(
        dict.fromkeys(
            value.strip()
            for value in candidates
            if value.strip()
        )
    )


def detect_sensitive(
    business_name: str,
) -> bool:
    normalized = business_name.lower()

    return any(
        sensitive_term in normalized
        for sensitive_term in SENSITIVE_TERMS
    )


def generate_column_description(
    table_business_name: str,
    column: MetadataColumn,
    business_name: str,
) -> str:
    normalized_name = business_name.lower()

    if column.is_primary_key:
        return (
            f"Unique identifier for each "
            f"{singularize(table_business_name).lower()} record."
        )

    if normalized_name in DATE_TERMS or "date" in normalized_name:
        return (
            f"Stores the {normalized_name} associated with "
            f"{table_business_name.lower()}."
        )

    if "status" in normalized_name:
        return (
            f"Indicates the current {normalized_name} of "
            f"{table_business_name.lower()}."
        )

    if "amount" in normalized_name or "balance" in normalized_name:
        return (
            f"Stores the monetary {normalized_name} associated with "
            f"{table_business_name.lower()}."
        )

    if "number" in normalized_name:
        return (
            f"Stores the {normalized_name} used to identify or reference "
            f"{table_business_name.lower()}."
        )

    if "name" in normalized_name:
        return (
            f"Stores the {normalized_name} associated with "
            f"{table_business_name.lower()}."
        )

    return (
        f"Stores the {normalized_name} value for "
        f"{table_business_name.lower()}."
    )


def generate_table_description(
    table: MetadataTable,
    table_business_name: str,
    generated_columns: list[GeneratedColumn],
) -> str:
    column_names = [
        column.business_name.lower()
        for column in generated_columns[:6]
    ]

    if column_names:
        included_fields = ", ".join(column_names[:-1])

        if len(column_names) > 1:
            included_fields += (
                f" and {column_names[-1]}"
            )
        else:
            included_fields = column_names[0]

        return (
            f"Stores information related to "
            f"{table_business_name.lower()}, including "
            f"{included_fields}."
        )

    return (
        f"Stores information related to "
        f"{table_business_name.lower()}."
    )


def generate_suggested_questions(
    table_business_name: str,
    columns: list[GeneratedColumn],
) -> list[str]:
    questions = [
        f"Show all {table_business_name.lower()}",
        f"How many {table_business_name.lower()} records are available?",
    ]

    for column in columns:
        name = column.business_name.lower()

        if "status" in name:
            questions.append(
                f"Show {table_business_name.lower()} by {name}"
            )

        if "date" in name or "expiry" in name:
            questions.append(
                f"Show {table_business_name.lower()} by {name}"
            )

        if "amount" in name or "balance" in name:
            questions.append(
                f"Show total {name} for {table_business_name.lower()}"
            )

        if len(questions) >= 6:
            break

    return list(dict.fromkeys(questions))[:6]


def generate_table_definition(
    table: MetadataTable,
) -> dict:
    table_business_name = (
        table.business_name
        or title_from_identifier(
            table.table_name
        )
    )

    generated_columns: list[
        GeneratedColumn
    ] = []

    for column in table.columns:
        business_name = (
            column.business_name
            or title_from_identifier(
                column.column_name
            )
        )

        sensitive = (
            column.is_sensitive
            or detect_sensitive(
                business_name
            )
        )

        classification = (
            "confidential"
            if sensitive
            else (
                column.classification
                or "internal"
            )
        )

        generated_columns.append(
            GeneratedColumn(
                column_id=column.id,
                technical_name=(
                    column.column_name
                ),
                business_name=business_name,
                description=(
                    column.description
                    or generate_column_description(
                        table_business_name,
                        column,
                        business_name,
                    )
                ),
                synonyms=create_synonyms(
                    column.column_name,
                    business_name,
                ),
                classification=classification,
                is_sensitive=sensitive,
            )
        )

    table_description = (
        table.description
        or generate_table_description(
            table,
            table_business_name,
            generated_columns,
        )
    )

    return {
        "table_id": table.id,
        "technical_name": (
            table.table_name
        ),
        "business_name": (
            table_business_name
        ),
        "description": (
            table_description
        ),
        "synonyms": create_synonyms(
            table.table_name,
            table_business_name,
        ),
        "suggested_questions": (
            generate_suggested_questions(
                table_business_name,
                generated_columns,
            )
        ),
        "columns": [
            {
                "column_id": item.column_id,
                "technical_name": (
                    item.technical_name
                ),
                "business_name": (
                    item.business_name
                ),
                "description": (
                    item.description
                ),
                "synonyms": item.synonyms,
                "classification": (
                    item.classification
                ),
                "is_sensitive": (
                    item.is_sensitive
                ),
            }
            for item in generated_columns
        ],
    }
