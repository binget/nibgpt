import re

from app.models.business_entity import (
    BusinessEntity,
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


def suggest_relationship(
    source: BusinessEntity,
    target: BusinessEntity,
) -> dict:
    source_name = source.name
    target_name = target.name

    source_text = normalize_text(
        " ".join(
            filter(
                None,
                [
                    source.name,
                    source.description,
                    source.synonyms,
                ],
            )
        )
    )

    target_text = normalize_text(
        " ".join(
            filter(
                None,
                [
                    target.name,
                    target.description,
                    target.synonyms,
                ],
            )
        )
    )

    confidence = 55
    reasons: list[str] = []

    relationship_name = "related to"
    inverse_name = "related to"
    relationship_type = "business"
    cardinality = "many_to_many"

    target_term = normalize_text(target.name)
    source_term = normalize_text(source.name)

    if target_term in source_text:
        confidence += 20

        relationship_name = "references"
        inverse_name = "is referenced by"
        cardinality = "many_to_one"

        reasons.append(
            f"{source_name} metadata refers to {target_name}."
        )

    if source_term in target_text:
        confidence += 20

        relationship_name = "is used by"
        inverse_name = "uses"
        cardinality = "one_to_many"

        reasons.append(
            f"{target_name} metadata refers to {source_name}."
        )

    if source.domain_id == target.domain_id:
        confidence += 10

        reasons.append(
            "Both entities belong to the same business domain."
        )

    if (
        source.approval_status == "approved"
        and target.approval_status == "approved"
    ):
        confidence += 10

        reasons.append(
            "Both business entities are approved."
        )

    if not reasons:
        reasons.append(
            "The entities were selected for manual relationship review."
        )

    return {
        "source_entity_id": source.id,
        "target_entity_id": target.id,
        "relationship_name": relationship_name,
        "inverse_relationship_name": inverse_name,
        "relationship_type": relationship_type,
        "cardinality": cardinality,
        "description": (
            f"Defines the business relationship between "
            f"{source_name} and {target_name}."
        ),
        "confidence": min(
            confidence,
            100,
        ),
        "reasons": reasons,
    }
