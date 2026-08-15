import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.metadata import (
    MetadataColumn,
    MetadataTable,
)


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "by",
    "for",
    "from",
    "give",
    "how",
    "i",
    "in",
    "is",
    "list",
    "me",
    "of",
    "on",
    "please",
    "report",
    "show",
    "the",
    "this",
    "to",
    "what",
    "with",
}


@dataclass
class ColumnMatch:
    column: MetadataColumn
    score: int = 0
    matched_terms: list[str] = field(
        default_factory=list
    )


@dataclass
class TableMatch:
    table: MetadataTable
    score: int = 0
    matched_terms: list[str] = field(
        default_factory=list
    )
    reasons: list[str] = field(
        default_factory=list
    )
    columns: list[ColumnMatch] = field(
        default_factory=list
    )


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    text = value.lower()
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_terms(prompt: str) -> list[str]:
    normalized = normalize_text(prompt)

    terms = [
        term
        for term in normalized.split()
        if len(term) >= 2
        and term not in STOP_WORDS
    ]

    # Remove duplicates while preserving order
    return list(dict.fromkeys(terms))


def detect_intent(prompt: str) -> str:
    normalized = normalize_text(prompt)

    if any(
        word in normalized
        for word in [
            "count",
            "how many",
            "number of",
        ]
    ):
        return "count"

    if any(
        word in normalized
        for word in [
            "total",
            "sum",
            "amount",
            "balance",
        ]
    ):
        return "aggregation"

    if any(
        word in normalized
        for word in [
            "trend",
            "growth",
            "monthly",
            "yearly",
            "daily",
        ]
    ):
        return "trend_analysis"

    if any(
        word in normalized
        for word in [
            "top",
            "highest",
            "lowest",
            "largest",
        ]
    ):
        return "ranking"

    if any(
        word in normalized
        for word in [
            "expired",
            "expiring",
            "overdue",
        ]
    ):
        return "expiry_monitoring"

    return "data_lookup"


def score_text(
    prompt: str,
    terms: list[str],
    value: str | None,
    exact_weight: int,
    term_weight: int,
) -> tuple[int, list[str]]:
    normalized_value = normalize_text(value)

    if not normalized_value:
        return 0, []

    score = 0
    matches: list[str] = []

    normalized_prompt = normalize_text(prompt)

    if (
        normalized_value
        and normalized_value in normalized_prompt
    ):
        score += exact_weight
        matches.append(normalized_value)

    for term in terms:
        if term in normalized_value:
            score += term_weight

            if term not in matches:
                matches.append(term)

    return score, matches


def calculate_column_match(
    prompt: str,
    terms: list[str],
    column: MetadataColumn,
) -> ColumnMatch:
    score = 0
    matches: list[str] = []

    fields = [
        (column.business_name, 45, 18),
        (column.column_name, 35, 14),
        (column.description, 25, 10),
    ]

    for value, exact_weight, term_weight in fields:
        field_score, field_matches = score_text(
            prompt,
            terms,
            value,
            exact_weight,
            term_weight,
        )

        score += field_score

        for match in field_matches:
            if match not in matches:
                matches.append(match)

    return ColumnMatch(
        column=column,
        score=score,
        matched_terms=matches,
    )


def calculate_table_match(
    prompt: str,
    terms: list[str],
    table: MetadataTable,
) -> TableMatch:
    score = 0
    matches: list[str] = []
    reasons: list[str] = []

    table_fields = [
        (
            table.business_name,
            100,
            35,
            "Business name matched",
        ),
        (
            table.table_name,
            80,
            28,
            "Technical table name matched",
        ),
        (
            table.description,
            55,
            18,
            "Business description matched",
        ),
        (
            table.department,
            30,
            12,
            "Department matched",
        ),
        (
            table.data_owner,
            25,
            10,
            "Data owner matched",
        ),
    ]

    for (
        value,
        exact_weight,
        term_weight,
        reason,
    ) in table_fields:
        field_score, field_matches = score_text(
            prompt,
            terms,
            value,
            exact_weight,
            term_weight,
        )

        if field_score > 0:
            score += field_score
            reasons.append(reason)

        for match in field_matches:
            if match not in matches:
                matches.append(match)

    column_matches: list[ColumnMatch] = []

    for column in table.columns:
        if (
            not column.is_enabled
            or not column.ai_access_allowed
        ):
            continue

        column_match = calculate_column_match(
            prompt,
            terms,
            column,
        )

        if column_match.score > 0:
            column_matches.append(column_match)

            # Column relevance contributes to table score
            score += min(
                column_match.score,
                55,
            )

    column_matches.sort(
        key=lambda item: item.score,
        reverse=True,
    )

    if column_matches:
        reasons.append(
            f"{len(column_matches)} relevant column(s) matched"
        )

    if table.business_name:
        score += 5

    if table.description:
        score += 5

    return TableMatch(
        table=table,
        score=score,
        matched_terms=matches,
        reasons=list(dict.fromkeys(reasons)),
        columns=column_matches[:10],
    )


def calculate_confidence(
    match: TableMatch,
) -> int:
    score = match.score

    if score >= 180:
        confidence = 98
    elif score >= 130:
        confidence = 92
    elif score >= 90:
        confidence = 84
    elif score >= 60:
        confidence = 72
    elif score >= 35:
        confidence = 58
    else:
        confidence = 40

    if not match.table.business_name:
        confidence -= 8

    if not match.table.description:
        confidence -= 8

    if not match.table.ai_access_allowed:
        confidence = min(confidence, 20)

    return max(
        0,
        min(confidence, 100),
    )


def create_suggested_questions(
    table: MetadataTable,
    columns: list[ColumnMatch],
) -> list[str]:
    table_name = (
        table.business_name
        or table.table_name.replace("_", " ")
    )

    suggestions = [
        f"Show all {table_name}",
        f"How many {table_name} records are available?",
    ]

    for column_match in columns[:3]:
        column_name = (
            column_match.column.business_name
            or column_match.column.column_name.replace(
                "_",
                " ",
            )
        )

        suggestions.append(
            f"Show {table_name} by {column_name}"
        )

    return list(dict.fromkeys(suggestions))[:5]


def analyze_prompt(
    database: Session,
    prompt: str,
    data_source_id: int | None = None,
    maximum_results: int = 5,
) -> dict:
    terms = extract_terms(prompt)
    intent = detect_intent(prompt)

    statement = (
        select(MetadataTable)
        .options(
            selectinload(
                MetadataTable.columns
            )
        )
        .where(
            MetadataTable.is_enabled.is_(True)
        )
    )

    if data_source_id is not None:
        statement = statement.where(
            MetadataTable.data_source_id
            == data_source_id
        )

    tables = list(
        database.scalars(statement).all()
    )

    matches: list[TableMatch] = []

    for table in tables:
        table_match = calculate_table_match(
            prompt=prompt,
            terms=terms,
            table=table,
        )

        if table_match.score > 0:
            matches.append(table_match)

    matches.sort(
        key=lambda item: item.score,
        reverse=True,
    )

    matches = matches[:maximum_results]

    warnings: list[str] = []

    if not terms:
        warnings.append(
            "The prompt does not contain enough meaningful search terms."
        )

    if not matches:
        warnings.append(
            "No matching business metadata was found."
        )

    if matches and not matches[0].table.ai_access_allowed:
        warnings.append(
            "The strongest metadata match does not allow AI access."
        )

    overall_confidence = (
        calculate_confidence(matches[0])
        if matches
        else 0
    )

    return {
        "prompt": prompt,
        "normalized_prompt": normalize_text(prompt),
        "intent": intent,
        "confidence": overall_confidence,
        "warnings": warnings,
        "matches": matches,
    }
