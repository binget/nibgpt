from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.data_source import DataSource
from app.models.metadata import MetadataTable


def percentage(
    completed: int,
    total: int,
) -> int:
    if total <= 0:
        return 0

    return round(
        (completed / total) * 100
    )


def maturity_level(
    score: int,
) -> str:
    if score >= 90:
        return "Excellent"

    if score >= 75:
        return "Good"

    if score >= 55:
        return "Developing"

    if score >= 30:
        return "Early Stage"

    return "Not Ready"


def readiness_status(
    score: int,
) -> str:
    if score >= 80:
        return "AI Ready"

    if score >= 60:
        return "Nearly Ready"

    if score >= 40:
        return "In Progress"

    return "Requires Attention"


def enterprise_label(
    score: int,
) -> str:
    if score >= 90:
        return "Enterprise AI Ready"

    if score >= 75:
        return "Strong Readiness"

    if score >= 55:
        return "Progressing Well"

    if score >= 35:
        return "Developing"

    return "Foundation Stage"


def calculate_domain_score(
    dictionary_percentage: int,
    knowledge_percentage: int,
    governance_percentage: int,
) -> int:
    return round(
        dictionary_percentage * 0.30
        + knowledge_percentage * 0.45
        + governance_percentage * 0.25
    )


def build_executive_dashboard(
    database: Session,
) -> dict:
    source_statement = (
        select(DataSource)
        .where(
            DataSource.is_active.is_(True)
        )
        .order_by(DataSource.name)
    )

    sources = list(
        database.scalars(
            source_statement
        ).all()
    )

    metadata_statement = (
        select(MetadataTable)
        .where(
            MetadataTable.is_discovered.is_(True)
        )
    )

    metadata_tables = list(
        database.scalars(
            metadata_statement
        ).all()
    )

    tables_by_source: dict[
        int,
        list[MetadataTable],
    ] = defaultdict(list)

    for table in metadata_tables:
        tables_by_source[
            table.data_source_id
        ].append(table)

    domains: list[dict] = []
    highlights: list[dict] = []

    for source in sources:
        source_tables = tables_by_source.get(
            source.id,
            [],
        )

        total_tables = len(source_tables)

        if total_tables == 0:
            domains.append(
                {
                    "data_source_id": source.id,
                    "domain_name": source.name,
                    "database_type": (
                        source.database_type
                    ),
                    "readiness_score": 0,
                    "maturity_level": "Not Ready",
                    "status": (
                        "Requires Attention"
                    ),
                    "approved_knowledge_percentage": 0,
                    "approved_dictionary_percentage": 0,
                    "governance_percentage": 0,
                    "requires_attention": True,
                    "attention_reason": (
                        "Business knowledge has not "
                        "yet been prepared."
                    ),
                }
            )

            continue

        approved_dictionary = sum(
            1
            for table in source_tables
            if (
                table.definition_status
                == "approved"
            )
        )

        approved_knowledge = sum(
            1
            for table in source_tables
            if (
                table.knowledge_status
                == "approved"
            )
        )

        governed_tables = sum(
            1
            for table in source_tables
            if (
                table.is_enabled
                and table.ai_access_allowed
                and table.classification
                in {
                    "public",
                    "internal",
                    "confidential",
                    "restricted",
                }
            )
        )

        dictionary_score = percentage(
            approved_dictionary,
            total_tables,
        )

        knowledge_score = percentage(
            approved_knowledge,
            total_tables,
        )

        governance_score = percentage(
            governed_tables,
            total_tables,
        )

        readiness_score = (
            calculate_domain_score(
                dictionary_percentage=(
                    dictionary_score
                ),
                knowledge_percentage=(
                    knowledge_score
                ),
                governance_percentage=(
                    governance_score
                ),
            )
        )

        needs_attention = (
            readiness_score < 60
        )

        attention_reason = None

        if knowledge_score < 40:
            attention_reason = (
                "AI knowledge coverage requires "
                "management attention."
            )

        elif dictionary_score < 60:
            attention_reason = (
                "Business definitions require "
                "additional review and approval."
            )

        elif governance_score < 80:
            attention_reason = (
                "AI governance coverage requires "
                "improvement."
            )

        domains.append(
            {
                "data_source_id": source.id,
                "domain_name": source.name,
                "database_type": (
                    source.database_type
                ),
                "readiness_score": (
                    readiness_score
                ),
                "maturity_level": (
                    maturity_level(
                        readiness_score
                    )
                ),
                "status": (
                    readiness_status(
                        readiness_score
                    )
                ),
                "approved_knowledge_percentage": (
                    knowledge_score
                ),
                "approved_dictionary_percentage": (
                    dictionary_score
                ),
                "governance_percentage": (
                    governance_score
                ),
                "requires_attention": (
                    needs_attention
                ),
                "attention_reason": (
                    attention_reason
                ),
            }
        )

    domain_scores = [
        domain["readiness_score"]
        for domain in domains
    ]

    enterprise_readiness = (
        round(
            sum(domain_scores)
            / len(domain_scores)
        )
        if domain_scores
        else 0
    )

    ai_ready_domains = [
        domain
        for domain in domains
        if domain["readiness_score"] >= 80
    ]

    attention_domains = [
        domain
        for domain in domains
        if domain["requires_attention"]
    ]

    governance_scores = [
        domain["governance_percentage"]
        for domain in domains
    ]

    knowledge_scores = [
        domain[
            "approved_knowledge_percentage"
        ]
        for domain in domains
    ]

    governance_compliance = (
        round(
            sum(governance_scores)
            / len(governance_scores)
        )
        if governance_scores
        else 0
    )

    knowledge_maturity = (
        round(
            sum(knowledge_scores)
            / len(knowledge_scores)
        )
        if knowledge_scores
        else 0
    )

    if ai_ready_domains:
        best_domain = max(
            ai_ready_domains,
            key=lambda item: item[
                "readiness_score"
            ],
        )

        highlights.append(
            {
                "severity": "success",
                "title": (
                    "Leading business area"
                ),
                "message": (
                    f"{best_domain['domain_name']} "
                    f"has reached "
                    f"{best_domain['readiness_score']}% "
                    f"AI readiness."
                ),
            }
        )

    if attention_domains:
        highest_priority = min(
            attention_domains,
            key=lambda item: item[
                "readiness_score"
            ],
        )

        highlights.append(
            {
                "severity": "warning",
                "title": (
                    "Area requiring attention"
                ),
                "message": (
                    f"{highest_priority['domain_name']} "
                    f"is currently at "
                    f"{highest_priority['readiness_score']}% "
                    f"readiness. "
                    f"{highest_priority['attention_reason']}"
                ),
            }
        )

    if governance_compliance >= 90:
        highlights.append(
            {
                "severity": "success",
                "title": (
                    "Strong AI governance"
                ),
                "message": (
                    "Enterprise AI governance "
                    "coverage is operating at a "
                    "strong level."
                ),
            }
        )
    elif governance_compliance < 70:
        highlights.append(
            {
                "severity": "warning",
                "title": (
                    "Governance improvement needed"
                ),
                "message": (
                    "Some business areas require "
                    "stronger AI access and data "
                    "classification controls."
                ),
            }
        )

    if not highlights:
        highlights.append(
            {
                "severity": "info",
                "title": (
                    "AI foundation in progress"
                ),
                "message": (
                    "NIBGPT is building approved "
                    "business knowledge across "
                    "connected systems."
                ),
            }
        )

    return {
        "enterprise_readiness": (
            enterprise_readiness
        ),
        "readiness_label": (
            enterprise_label(
                enterprise_readiness
            )
        ),
        "connected_business_systems": (
            len(sources)
        ),
        "ai_ready_business_systems": (
            len(ai_ready_domains)
        ),
        "systems_requiring_attention": (
            len(attention_domains)
        ),
        "governance_compliance": (
            governance_compliance
        ),
        "knowledge_maturity": (
            knowledge_maturity
        ),
        "domains": sorted(
            domains,
            key=lambda item: item[
                "readiness_score"
            ],
            reverse=True,
        ),
        "highlights": highlights,
    }
