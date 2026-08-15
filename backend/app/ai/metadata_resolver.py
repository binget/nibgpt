import json
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.metadata import (
    MetadataColumn,
    MetadataTable,
)


@dataclass
class ColumnResolution:
    column: MetadataColumn
    score: int
    confidence: int
    matched_terms: list[str] = field(
        default_factory=list
    )
    reasons: list[str] = field(
        default_factory=list
    )


@dataclass
class TableResolution:
    table: MetadataTable
    score: int
    confidence: int
    matched_terms: list[str] = field(
        default_factory=list
    )
    reasons: list[str] = field(
        default_factory=list
    )
    columns: list[ColumnResolution] = field(
        default_factory=list
    )


GENERAL_LANGUAGE_EQUIVALENTS = {
    "records": ["record"],
    "entries": ["entry", "record"],
    "number": ["count"],
    "total": ["sum"],
    "highest": ["maximum", "top"],
    "lowest": ["minimum", "bottom"],
    "expired": ["expiry", "expiry date"],
    "expires": ["expiry", "expiry date"],
    "expiring": ["expiry", "expiry date"],
    "approved": ["approval status"],
    "rejected": ["rejection status"],
    "pending": ["pending status"],
    "available": ["availability status"],
}

def singularize_term(value: str) -> str:
    if value.endswith("ies") and len(value) > 3:
        return value[:-3] + "y"

    if value.endswith("s") and not value.endswith("ss"):
        return value[:-1]

    return value


def normalize_text(value: str | None) -> str:
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


def parse_saved_terms(
    value: str | None,
) -> list[str]:
    if not value:
        return []

    try:
        parsed = json.loads(value)

        if isinstance(parsed, list):
            return [
                normalize_text(str(item))
                for item in parsed
                if normalize_text(str(item))
            ]

    except (json.JSONDecodeError, TypeError):
        pass

    return [
        normalize_text(item)
        for item in re.split(r"[,;\n]+", value)
        if normalize_text(item)
    ]


def expand_terms(
    keywords: list[str],
) -> list[str]:
    expanded: list[str] = []

    for keyword in keywords:
        normalized = normalize_text(keyword)

        if not normalized:
            continue

        expanded.append(normalized)

        singular = singularize_term(normalized)

        if singular != normalized:
            expanded.append(singular)

        for equivalent in GENERAL_LANGUAGE_EQUIVALENTS.get(
            normalized,
            [],
        ):
            expanded.append(
                normalize_text(equivalent)
            )

    return list(dict.fromkeys(expanded))


def match_field(
    prompt: str,
    terms: list[str],
    value: str | None,
    exact_score: int,
    partial_score: int,
) -> tuple[int, list[str]]:
    normalized_value = normalize_text(value)

    if not normalized_value:
        return 0, []

    normalized_prompt = normalize_text(prompt)

    score = 0
    matched_terms: list[str] = []

    if normalized_value in normalized_prompt:
        score += exact_score
        matched_terms.append(normalized_value)

    for term in terms:
        if not term:
            continue

        if term == normalized_value:
            score += exact_score

            if term not in matched_terms:
                matched_terms.append(term)

        elif term in normalized_value:
            score += partial_score

            if term not in matched_terms:
                matched_terms.append(term)

        elif normalized_value in term:
            score += max(
                1,
                partial_score // 2,
            )

            if term not in matched_terms:
                matched_terms.append(term)

    return score, matched_terms


def score_column(
    prompt: str,
    terms: list[str],
    column: MetadataColumn,
) -> ColumnResolution:
    score = 0
    matches: list[str] = []
    reasons: list[str] = []

    fields = [
        (
            column.business_name,
            70,
            25,
            "Column business name matched",
        ),
        (
            column.column_name,
            55,
            20,
            "Technical column name matched",
        ),
        (
            column.description,
            35,
            12,
            "Column description matched",
        ),
    ]

    for value, exact_score, partial_score, reason in fields:
        field_score, field_matches = match_field(
            prompt,
            terms,
            value,
            exact_score,
            partial_score,
        )

        if field_score > 0:
            score += field_score
            reasons.append(reason)

        for item in field_matches:
            if item not in matches:
                matches.append(item)

    synonyms = parse_saved_terms(
        column.synonyms
    )

    for synonym in synonyms:
        synonym_score, synonym_matches = match_field(
            prompt,
            terms,
            synonym,
            65,
            23,
        )

        if synonym_score > 0:
            score += synonym_score
            reasons.append(
                "Column synonym matched"
            )

        for item in synonym_matches:
            if item not in matches:
                matches.append(item)

    if column.definition_status == "approved":
        score += 10
        reasons.append(
            "Column definition is approved"
        )

    confidence = score_to_confidence(score)

    return ColumnResolution(
        column=column,
        score=score,
        confidence=confidence,
        matched_terms=matches,
        reasons=list(dict.fromkeys(reasons)),
    )


def score_table(
    prompt: str,
    terms: list[str],
    table: MetadataTable,
) -> TableResolution:
    score = 0
    matches: list[str] = []
    reasons: list[str] = []

    fields = [
        (
            table.business_name,
            120,
            40,
            "Table business name matched",
        ),
        (
            table.table_name,
            90,
            30,
            "Technical table name matched",
        ),
        (
            table.description,
            60,
            20,
            "Table description matched",
        ),
        (
            table.department,
            30,
            10,
            "Department matched",
        ),
        (
            table.data_owner,
            25,
            8,
            "Data owner matched",
        ),
    ]

    for value, exact_score, partial_score, reason in fields:
        field_score, field_matches = match_field(
            prompt,
            terms,
            value,
            exact_score,
            partial_score,
        )

        if field_score > 0:
            score += field_score
            reasons.append(reason)

        for item in field_matches:
            if item not in matches:
                matches.append(item)

    synonyms = parse_saved_terms(
        table.synonyms
    )

    for synonym in synonyms:
        synonym_score, synonym_matches = match_field(
            prompt,
            terms,
            synonym,
            100,
            35,
        )

        if synonym_score > 0:
            score += synonym_score
            reasons.append(
                "Table synonym matched"
            )

        for item in synonym_matches:
            if item not in matches:
                matches.append(item)

    suggested_questions = parse_saved_terms(
        table.suggested_questions
    )

    for question in suggested_questions:
        question_score, question_matches = match_field(
            prompt,
            terms,
            question,
            55,
            15,
        )

        if question_score > 0:
            score += question_score
            reasons.append(
                "Approved question pattern matched"
            )

        for item in question_matches:
            if item not in matches:
                matches.append(item)

    column_matches: list[
        ColumnResolution
    ] = []

    for column in table.columns:
        if (
            not column.is_enabled
            or not column.is_discovered
            or not column.ai_access_allowed
        ):
            continue

        column_result = score_column(
            prompt,
            terms,
            column,
        )

        if column_result.score <= 0:
            continue

        column_matches.append(
            column_result
        )

        score += min(
            column_result.score,
            70,
        )

    column_matches.sort(
        key=lambda item: item.score,
        reverse=True,
    )

    if column_matches:
        reasons.append(
            f"{len(column_matches)} relevant column(s) matched"
        )

    if table.definition_status == "approved":
        score += 20
        reasons.append(
            "Table business definition is approved"
        )

    if not table.ai_access_allowed:
        reasons.append(
            "AI access is blocked for this table"
        )

    confidence = score_to_confidence(score)

    if not table.ai_access_allowed:
        confidence = min(
            confidence,
            20,
        )

    return TableResolution(
        table=table,
        score=score,
        confidence=confidence,
        matched_terms=matches,
        reasons=list(dict.fromkeys(reasons)),
        columns=column_matches[:12],
    )


def score_to_confidence(score: int) -> int:
    if score >= 300:
        return 99

    if score >= 220:
        return 96

    if score >= 160:
        return 92

    if score >= 110:
        return 86

    if score >= 75:
        return 78

    if score >= 45:
        return 66

    if score >= 20:
        return 52

    return 35


def resolve_metadata(
    database: Session,
    prompt: str,
    keywords: list[str],
    data_source_id: int | None = None,
    maximum_results: int = 5,
) -> list[TableResolution]:
    expanded_terms = expand_terms(keywords)

    statement = (
        select(MetadataTable)
        .options(
            selectinload(
                MetadataTable.columns
            )
        )
        .where(
            MetadataTable.is_enabled.is_(True),
            MetadataTable.is_discovered.is_(True),
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

    matches: list[TableResolution] = []

    for table in tables:
        result = score_table(
            prompt,
            expanded_terms,
            table,
        )

        if result.score > 0:
            matches.append(result)

    matches.sort(
        key=lambda item: item.score,
        reverse=True,
    )

    return matches[:maximum_results]
