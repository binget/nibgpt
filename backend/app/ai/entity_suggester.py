import json
import re

from app.models.metadata import MetadataTable


TECHNICAL_PREFIXES = {
    "tbl",
    "mst",
    "master",
    "dim",
    "fact",
    "vw",
    "view",
}


def normalize_identifier(
    value: str,
) -> list[str]:
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

    words = [
        word.lower()
        for word in value.split()
        if word
    ]

    return [
        word
        for word in words
        if word not in TECHNICAL_PREFIXES
    ]


def title_from_identifier(
    value: str,
) -> str:
    return " ".join(
        normalize_identifier(value)
    ).title()


def parse_list(
    value: str | None,
) -> list[str]:
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
        for item in re.split(
            r"[,;\n]+",
            value,
        )
        if item.strip()
    ]


def infer_domain_name(
    table: MetadataTable,
    source_name: str,
) -> str:
    if table.department:
        return table.department

    if source_name:
        return source_name

    words = normalize_identifier(
        table.table_name
    )

    if words:
        return words[0].title()

    return "General Business"


def infer_entity_name(
    table: MetadataTable,
) -> str:
    if table.business_name:
        return table.business_name

    words = normalize_identifier(
        table.table_name
    )

    if len(words) > 1:
        candidate_words = words[-2:]
    else:
        candidate_words = words

    return " ".join(
        candidate_words
    ).title()


def suggest_business_entity(
    table: MetadataTable,
    source_name: str,
) -> dict:
    entity_name = infer_entity_name(table)

    description = (
        table.business_purpose
        or table.description
        or (
            f"Represents the business concept of "
            f"{entity_name.lower()} within "
            f"{source_name}."
        )
    )

    synonyms = []

    synonyms.extend(
        parse_list(table.synonyms)
    )

    synonyms.extend(
        parse_list(table.business_terms)
    )

    synonyms.append(
        entity_name.lower()
    )

    synonyms.append(
        table.table_name
        .replace("_", " ")
        .lower()
    )

    synonyms = list(
        dict.fromkeys(
            synonym
            for synonym in synonyms
            if synonym
        )
    )

    reasons = [
        "The suggestion was generated from approved metadata.",
        f"The source system is {source_name}.",
        f"The physical table is {table.table_name}.",
    ]

    confidence = 55

    if table.business_name:
        confidence += 15
        reasons.append(
            "An existing business name was available."
        )

    if table.description:
        confidence += 10
        reasons.append(
            "An existing business description was available."
        )

    if table.definition_status == "approved":
        confidence += 10
        reasons.append(
            "The Business Dictionary definition is approved."
        )

    if table.knowledge_status == "approved":
        confidence += 10
        reasons.append(
            "The Knowledge Profile is approved."
        )

    return {
        "metadata_table_id": table.id,
        "suggested_domain_name": (
            infer_domain_name(
                table,
                source_name,
            )
        ),
        "suggested_entity_name": (
            entity_name
        ),
        "description": description,
        "synonyms": synonyms[:20],
        "confidence": min(
            confidence,
            100,
        ),
        "reasons": reasons,
    }
