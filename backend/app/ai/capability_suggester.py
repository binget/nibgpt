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


def infer_capability_name(
    entity: BusinessEntity,
) -> str:
    entity_name = entity.name.strip()

    management_suffixes = {
        "request": "Request Processing",
        "requests": "Request Processing",
        "approval": "Approval Management",
        "transaction": "Transaction Processing",
        "transactions": "Transaction Processing",
        "payment": "Payment Processing",
        "payments": "Payment Processing",
        "settlement": "Settlement Management",
        "report": "Reporting",
        "reports": "Reporting",
    }

    normalized_name = normalize_text(
        entity_name
    )

    for term, capability_name in (
        management_suffixes.items()
    ):
        if term in normalized_name:
            return capability_name

    if normalized_name.endswith(
        "management"
    ):
        return entity_name

    return f"{entity_name} Management"


def suggest_capability(
    domain_id: int,
    entities: list[BusinessEntity],
) -> dict:
    if not entities:
        return {
            "domain_id": domain_id,
            "suggested_name": (
                "Business Operations"
            ),
            "description": (
                "Represents a business capability "
                "within the selected domain."
            ),
            "capability_type": "operational",
            "maturity_level": "developing",
            "suggested_entity_ids": [],
            "confidence": 40,
            "reasons": [
                "No business entities were selected.",
            ],
        }

    primary_entity = entities[0]

    suggested_name = infer_capability_name(
        primary_entity
    )

    entity_names = [
        entity.name
        for entity in entities
    ]

    description = (
        f"Supports business operations related to "
        f"{', '.join(entity_names)} within the "
        f"selected business domain."
    )

    confidence = 55
    reasons: list[str] = []

    if all(
        entity.domain_id == domain_id
        for entity in entities
    ):
        confidence += 15

        reasons.append(
            "All selected entities belong to "
            "the selected business domain."
        )

    approved_entities = [
        entity
        for entity in entities
        if (
            entity.approval_status
            == "approved"
        )
    ]

    if approved_entities:
        confidence += min(
            len(approved_entities) * 5,
            20,
        )

        reasons.append(
            f"{len(approved_entities)} selected "
            "entity or entities are approved."
        )

    if all(
        entity.table_mappings
        for entity in entities
    ):
        confidence += 10

        reasons.append(
            "All selected entities have physical "
            "data mappings."
        )

    if not reasons:
        reasons.append(
            "The suggestion requires manual "
            "business review."
        )

    return {
        "domain_id": domain_id,
        "suggested_name": suggested_name,
        "description": description,
        "capability_type": "operational",
        "maturity_level": "developing",
        "suggested_entity_ids": [
            entity.id
            for entity in entities
        ],
        "confidence": min(
            confidence,
            100,
        ),
        "reasons": reasons,
    }
