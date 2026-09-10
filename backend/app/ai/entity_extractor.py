import re
from dataclasses import dataclass


@dataclass
class ExtractedEntity:
    value: str
    entity_type: str
    confidence: int


STOP_WORDS = {
    "a",
    "all",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "give",
    "how",
    "i",
    "in",
    "is",
    "it",
    "list",
    "me",
    "of",
    "on",
    "or",
    "please",
    "show",
    "that",
    "the",
    "their",
    "this",
    "to",
    "which",
    "with",
}


TIME_PATTERNS = [
    r"\btoday\b",
    r"\byesterday\b",
    r"\btomorrow\b",
    r"\bthis week\b",
    r"\blast week\b",
    r"\bnext week\b",

    r"\blast \d+ months?\b",
    r"\bpast \d+ months?\b",
    r"\bprevious \d+ months?\b",

    r"\bthis month\b",
    r"\blast month\b",
    r"\bnext month\b",
    r"\bthis year\b",
    r"\blast year\b",
    r"\bnext year\b",
    r"\bwithin the next \d+ days\b",
    r"\bin the last \d+ days\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
]


STATUS_TERMS = {
    "active",
    "inactive",
    "available",
    "assigned",
    "unassigned",
    "approved",
    "rejected",
    "pending",
    "completed",
    "failed",
    "expired",
    "expiring",
    "overdue",
    "open",
    "closed",
    "cancelled",
}


AGGREGATION_TERMS = {
    "count",
    "total",
    "sum",
    "average",
    "avg",
    "minimum",
    "maximum",
    "min",
    "max",
}


def normalize_text(value: str) -> str:
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


def extract_time_expressions(
    normalized_prompt: str,
) -> list[str]:
    expressions: list[str] = []

    for pattern in TIME_PATTERNS:
        expressions.extend(
            re.findall(
                pattern,
                normalized_prompt,
            )
        )

    return list(dict.fromkeys(expressions))


def extract_keywords(
    normalized_prompt: str,
    time_expressions: list[str],
) -> list[str]:
    cleaned_prompt = normalized_prompt

    for expression in time_expressions:
        cleaned_prompt = cleaned_prompt.replace(
            expression,
            " ",
        )

    words = [
        word
        for word in cleaned_prompt.split()
        if (
            len(word) >= 2
            and word not in STOP_WORDS
        )
    ]

    return list(dict.fromkeys(words))


def extract_entities(
    prompt: str,
) -> dict:
    normalized_prompt = normalize_text(prompt)

    time_expressions = extract_time_expressions(
        normalized_prompt
    )

    keywords = extract_keywords(
        normalized_prompt,
        time_expressions,
    )

    status_terms = [
        word
        for word in keywords
        if word in STATUS_TERMS
    ]

    aggregation_terms = [
        word
        for word in keywords
        if word in AGGREGATION_TERMS
    ]

    entities: list[ExtractedEntity] = []

    for expression in time_expressions:
        entities.append(
            ExtractedEntity(
                value=expression,
                entity_type="time",
                confidence=98,
            )
        )

    for term in status_terms:
        entities.append(
            ExtractedEntity(
                value=term,
                entity_type="status",
                confidence=95,
            )
        )

    for term in aggregation_terms:
        entities.append(
            ExtractedEntity(
                value=term,
                entity_type="aggregation",
                confidence=98,
            )
        )

    reserved_terms = set(
        time_expressions
        + status_terms
        + aggregation_terms
    )

    for keyword in keywords:
        if keyword in reserved_terms:
            continue

        entities.append(
            ExtractedEntity(
                value=keyword,
                entity_type="business_term",
                confidence=78,
            )
        )

    return {
        "normalized_prompt": normalized_prompt,
        "keywords": keywords,
        "time_expressions": time_expressions,
        "status_terms": status_terms,
        "aggregation_terms": aggregation_terms,
        "entities": entities,
    }
