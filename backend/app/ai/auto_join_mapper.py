import json
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from sqlalchemy.orm import selectinload

from app.models.business_entity import (
    BusinessEntity,
)
from app.models.business_relationship import (
    BusinessEntityRelationship,
)
from app.models.business_join_mapping import (
    BusinessRelationshipJoinMapping,
)
from app.models.metadata import (
    MetadataColumn,
    MetadataTable,
)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

MAPPING_TYPE_SCORES = {
    "primary": 100,
    "supporting": 55,
    "reference": 35,
}

AUTO_APPROVAL_CONFIDENCE = 95

MINIMUM_ACCEPTABLE_CONFIDENCE = 70

UNIQUE_WINNER_MARGIN = 8


# ---------------------------------------------------------
# Result structures
# ---------------------------------------------------------

@dataclass
class AutoJoinCandidate:
    source_table: MetadataTable
    source_column: MetadataColumn

    target_table: MetadataTable
    target_column: MetadataColumn

    score: int
    confidence: int

    reasons: list[str] = field(
        default_factory=list
    )


@dataclass
class AutoJoinResolution:
    relationship_id: int

    status: str

    candidate: (
        AutoJoinCandidate | None
    ) = None

    candidates: list[
        AutoJoinCandidate
    ] = field(
        default_factory=list
    )

    can_auto_approve: bool = False

    message: str = ""

    existing_mapping: (
        BusinessRelationshipJoinMapping
        | None
    ) = None


# ---------------------------------------------------------
# Text helpers
# ---------------------------------------------------------

def normalize_text(
    value: str | None,
) -> str:
    if not value:
        return ""

    value = value.lower()

    value = re.sub(
        r"[_\-]+",
        " ",
        value,
    )

    value = re.sub(
        r"[^a-z0-9\s]+",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def singularize(
    value: str,
) -> str:
    value = normalize_text(
        value
    )

    if value.endswith("ies"):
        return (
            value[:-3] + "y"
        )

    if (
        value.endswith("s")
        and not value.endswith("ss")
    ):
        return value[:-1]

    return value


def parse_synonyms(
    value,
) -> list[str]:
    if not value:
        return []

    if isinstance(
        value,
        list,
    ):
        return [
            str(item)
            for item in value
        ]

    if isinstance(
        value,
        str,
    ):
        try:
            parsed = json.loads(
                value
            )

            if isinstance(
                parsed,
                list,
            ):
                return [
                    str(item)
                    for item in parsed
                ]

        except Exception:
            pass

        return [
            item.strip()
            for item in value.split(",")
            if item.strip()
        ]

    return []


# ---------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------

def is_usable_table(
    table: MetadataTable,
) -> bool:
    return (
        table.is_discovered
        and table.is_enabled
        and table.ai_access_allowed
    )


def is_usable_column(
    column: MetadataColumn,
) -> bool:
    return (
        column.is_discovered
        and column.is_enabled
        and column.ai_access_allowed
    )


def type_family(
    data_type: str | None,
) -> str:
    normalized = normalize_text(
        data_type
    )

    if any(
        item in normalized
        for item in {
            "char",
            "varchar",
            "text",
            "string",
        }
    ):
        return "text"

    if any(
        item in normalized
        for item in {
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
        }
    ):
        return "numeric"

    if any(
        item in normalized
        for item in {
            "date",
            "datetime",
            "timestamp",
            "time",
        }
    ):
        return "date"

    if any(
        item in normalized
        for item in {
            "bool",
            "boolean",
            "bit",
        }
    ):
        return "boolean"

    return normalized


def compatible_types(
    source: MetadataColumn,
    target: MetadataColumn,
) -> bool:
    source_family = type_family(
        source.data_type
    )

    target_family = type_family(
        target.data_type
    )

    return (
        source_family
        == target_family
    )


# ---------------------------------------------------------
# Table resolution
# ---------------------------------------------------------

def get_active_entity_mappings(
    entity: BusinessEntity,
):
    mappings = [
        mapping
        for mapping
        in entity.table_mappings
        if mapping.is_active
    ]

    if not mappings:
        return []

    primary_mappings = [
        mapping
        for mapping in mappings
        if mapping.mapping_type
        == "primary"
    ]

    # If an entity has a primary physical representation,
    # auto join resolution should start from primary tables
    # only. Supporting/reference tables are fallback metadata.
    if primary_mappings:
        primary_mappings.sort(
            key=lambda mapping:
                mapping.confidence,
            reverse=True,
        )

        return primary_mappings

    mappings.sort(
        key=lambda mapping: (
            MAPPING_TYPE_SCORES.get(
                mapping.mapping_type,
                0,
            ),
            mapping.confidence,
        ),
        reverse=True,
    )

    return mappings


def load_entity_tables(
    database: Session,
    entity: BusinessEntity,
) -> list[
    tuple[
        MetadataTable,
        object,
    ]
]:
    results = []

    mappings = (
        get_active_entity_mappings(
            entity
        )
    )

    for mapping in mappings:
        statement = (
    select(MetadataTable)
    .options(
        selectinload(
            MetadataTable.columns
        )
    )
    .where(
        MetadataTable.id
        == mapping.metadata_table_id
    )
    )

        table = database.scalar(
        statement
    )
    

    results.append(
            (
                table,
                mapping,
            )
        )

    return results


# ---------------------------------------------------------
# Column scoring
# ---------------------------------------------------------

def column_terms(
    column: MetadataColumn,
) -> set[str]:
    values = {
        normalize_text(
            column.column_name
        ),
        normalize_text(
            column.business_name
        ),
    }

    for synonym in parse_synonyms(
        getattr(
            column,
            "synonyms",
            None,
        )
    ):
        values.add(
            normalize_text(
                synonym
            )
        )

    return {
        item
        for item in values
        if item
    }


def score_column_pair(
    relationship: (
        BusinessEntityRelationship
    ),
    source_table: MetadataTable,
    source_column: MetadataColumn,
    target_table: MetadataTable,
    target_column: MetadataColumn,
    source_mapping,
    target_mapping,
) -> AutoJoinCandidate | None:

    # --------------------------------------------------
    # Safety
    # --------------------------------------------------

        # Different business entities must not resolve
    # to the same physical table during automatic
    # join discovery.
    if (
        relationship.source_entity_id
        != relationship.target_entity_id
        and source_table.id
        == target_table.id
    ):
        return None

    if (
        source_table.data_source_id
        != target_table.data_source_id
    ):
        return None

    if (
        relationship.source_entity_id
        != relationship.target_entity_id
        and source_table.id
        == target_table.id
        and source_column.id
        == target_column.id
    ):
        return None

    if not compatible_types(
        source_column,
        target_column,
    ):
        return None

    score = 0

    reasons: list[str] = []

    relationship_name = normalize_text(
        relationship.relationship_name
    )

    source_name = normalize_text(
        source_column.column_name
    )

    target_name = normalize_text(
        target_column.column_name
    )

    source_business = normalize_text(
        source_column.business_name
    )

    target_business = normalize_text(
        target_column.business_name
    )

    source_terms = column_terms(
        source_column
    )

    target_terms = column_terms(
        target_column
    )

    # --------------------------------------------------
    # Table mapping priority
    # --------------------------------------------------

    source_mapping_score = (
        MAPPING_TYPE_SCORES.get(
            source_mapping.mapping_type,
            0,
        )
    )

    target_mapping_score = (
        MAPPING_TYPE_SCORES.get(
            target_mapping.mapping_type,
            0,
        )
    )

    score += round(
        (
            source_mapping_score
            + target_mapping_score
        )
        / 10
    )

    if (
        source_mapping.mapping_type
        == "primary"
        and target_mapping.mapping_type
        == "primary"
    ):
        score += 20

        reasons.append(
            "Primary table to primary table mapping."
        )

    # --------------------------------------------------
    # Exact physical column match
    # --------------------------------------------------

    if (
        source_name
        and source_name
        == target_name
    ):
        score += 45

        reasons.append(
            "Physical column names match exactly."
        )

    # --------------------------------------------------
    # Exact business-name match
    # --------------------------------------------------

    if (
        source_business
        and source_business
        == target_business
    ):
        score += 40

        reasons.append(
            "Business column names match exactly."
        )

    # --------------------------------------------------
    # Semantic relationship match
    # --------------------------------------------------

    if relationship_name:
        if (
            relationship_name
            in source_terms
        ):
            score += 35

            reasons.append(
                "Source column matches relationship name."
            )

        if (
            relationship_name
            in target_terms
        ):
            score += 35

            reasons.append(
                "Target column matches relationship name."
            )

    # --------------------------------------------------
    # Shared synonyms/business terminology
    # --------------------------------------------------

    common_terms = (
        source_terms
        & target_terms
    )

    if common_terms:
        score += min(
            25,
            len(common_terms)
            * 12,
        )

        reasons.append(
            "Source and target columns share business terminology."
        )

    # --------------------------------------------------
    # PK / FK style preference
    # --------------------------------------------------

    if (
        source_column.is_primary_key
        != target_column.is_primary_key
    ):
        score += 8

        reasons.append(
            "Primary-key to reference-column pattern detected."
        )

    # --------------------------------------------------
    # Same data source
    # --------------------------------------------------

    score += 10

    reasons.append(
        "Tables belong to the same data source."
    )

    # --------------------------------------------------
    # Convert score to confidence
    # --------------------------------------------------

    confidence = min(
        100,
        max(
            0,
            score,
        ),
    )

    return AutoJoinCandidate(
        source_table=source_table,
        source_column=source_column,
        target_table=target_table,
        target_column=target_column,
        score=score,
        confidence=confidence,
        reasons=list(
            dict.fromkeys(
                reasons
            )
        ),
    )


# ---------------------------------------------------------
# Existing mapping
# ---------------------------------------------------------

def load_existing_approved_mapping(
    database: Session,
    relationship_id: int,
):
    statement = (
        select(
            BusinessRelationshipJoinMapping
        )
        .where(
            BusinessRelationshipJoinMapping.relationship_id
            == relationship_id,
            BusinessRelationshipJoinMapping.approval_status
            == "approved",
            BusinessRelationshipJoinMapping.is_active
            .is_(True),
        )
        .order_by(
            BusinessRelationshipJoinMapping.id
            .desc()
        )
    )

    return database.scalar(
        statement
    )


# ---------------------------------------------------------
# Main resolver
# ---------------------------------------------------------

def resolve_relationship_join(
    database: Session,
    relationship_id: int,
) -> AutoJoinResolution:

    relationship = database.get(
        BusinessEntityRelationship,
        relationship_id,
    )

    if relationship is None:
        return AutoJoinResolution(
            relationship_id=relationship_id,
            status="not_found",
            message=(
                "Business relationship was not found."
            ),
        )

    if (
        relationship.approval_status
        != "approved"
        or not relationship.is_active
    ):
        return AutoJoinResolution(
            relationship_id=relationship_id,
            status="relationship_not_approved",
            message=(
                "The business relationship must be "
                "approved and active."
            ),
        )

    # --------------------------------------------------
    # Existing approved mapping wins
    # --------------------------------------------------

    existing_mapping = (
        load_existing_approved_mapping(
            database=database,
            relationship_id=(
                relationship_id
            ),
        )
    )

    if existing_mapping:
        return AutoJoinResolution(
            relationship_id=relationship_id,
            status="already_resolved",
            existing_mapping=(
                existing_mapping
            ),
            can_auto_approve=True,
            message=(
                "An approved physical join mapping "
                "already exists."
            ),
        )

    # --------------------------------------------------
    # Load source and target entities
    # --------------------------------------------------

    source_entity = database.get(
        BusinessEntity,
        relationship.source_entity_id,
    )

    target_entity = database.get(
        BusinessEntity,
        relationship.target_entity_id,
    )

    if (
        source_entity is None
        or target_entity is None
    ):
        return AutoJoinResolution(
            relationship_id=relationship_id,
            status="entity_not_found",
            message=(
                "Source or target business entity "
                "could not be found."
            ),
        )

    source_tables = load_entity_tables(
        database=database,
        entity=source_entity,
    )

    target_tables = load_entity_tables(
        database=database,
        entity=target_entity,
    )

    if (
        not source_tables
        or not target_tables
    ):
        return AutoJoinResolution(
            relationship_id=relationship_id,
            status="table_mapping_missing",
            message=(
                "One or both entities do not have "
                "usable physical table mappings."
            ),
        )

    # --------------------------------------------------
    # Generate candidates
    # --------------------------------------------------

    candidates: list[
        AutoJoinCandidate
    ] = []

    for (
        source_table,
        source_mapping,
    ) in source_tables:

        for (
            target_table,
            target_mapping,
        ) in target_tables:

            if (
                source_table.data_source_id
                != target_table.data_source_id
            ):
                continue

            for source_column in (
                source_table.columns
            ):
                if not is_usable_column(
                    source_column
                ):
                    continue

                for target_column in (
                    target_table.columns
                ):
                    if not is_usable_column(
                        target_column
                    ):
                        continue

                    candidate = (
                        score_column_pair(
                            relationship=(
                                relationship
                            ),
                            source_table=(
                                source_table
                            ),
                            source_column=(
                                source_column
                            ),
                            target_table=(
                                target_table
                            ),
                            target_column=(
                                target_column
                            ),
                            source_mapping=(
                                source_mapping
                            ),
                            target_mapping=(
                                target_mapping
                            ),
                        )
                    )

                    if candidate:
                        candidates.append(
                            candidate
                        )

    candidates.sort(
        key=lambda item: (
            item.score
        ),
        reverse=True,
    )

    if not candidates:
        return AutoJoinResolution(
            relationship_id=relationship_id,
            status="no_candidate",
            message=(
                "No compatible physical join "
                "candidate could be found."
            ),
        )

    # --------------------------------------------------
    # Best candidate
    # --------------------------------------------------

    best = candidates[0]

    second_score = (
        candidates[1].score
        if len(candidates) > 1
        else 0
    )

    winner_margin = (
        best.score
        - second_score
    )

    unique_best = (
        len(candidates) == 1
        or winner_margin
        >= UNIQUE_WINNER_MARGIN
    )

    can_auto_approve = (
        best.confidence
        >= AUTO_APPROVAL_CONFIDENCE
        and unique_best
    )

    if best.confidence < (
        MINIMUM_ACCEPTABLE_CONFIDENCE
    ):
        return AutoJoinResolution(
            relationship_id=relationship_id,
            status="low_confidence",
            candidate=best,
            candidates=candidates[:5],
            can_auto_approve=False,
            message=(
                "Join candidates were found, "
                "but confidence is too low."
            ),
        )

    if not unique_best:
        return AutoJoinResolution(
            relationship_id=relationship_id,
            status="requires_review",
            candidate=best,
            candidates=candidates[:5],
            can_auto_approve=False,
            message=(
                "Multiple similar physical join "
                "candidates were found. "
                "Administrator review is required."
            ),
        )

    return AutoJoinResolution(
        relationship_id=relationship_id,
        status=(
            "auto_approvable"
            if can_auto_approve
            else "suggested"
        ),
        candidate=best,
        candidates=candidates[:5],
        can_auto_approve=(
            can_auto_approve
        ),
        message=(
            "A unique physical join candidate "
            "was resolved."
        ),
    )


def load_exact_existing_mapping(
    database: Session,
    relationship_id: int,
    candidate: AutoJoinCandidate,
) -> (
    BusinessRelationshipJoinMapping
    | None
):
    statement = (
        select(
            BusinessRelationshipJoinMapping
        )
        .where(
            BusinessRelationshipJoinMapping.relationship_id
            == relationship_id,

            BusinessRelationshipJoinMapping.source_metadata_table_id
            == candidate.source_table.id,

            BusinessRelationshipJoinMapping.source_metadata_column_id
            == candidate.source_column.id,

            BusinessRelationshipJoinMapping.target_metadata_table_id
            == candidate.target_table.id,

            BusinessRelationshipJoinMapping.target_metadata_column_id
            == candidate.target_column.id,
        )
        .order_by(
            BusinessRelationshipJoinMapping.id.desc()
        )
    )

    return database.scalar(
        statement
    )

# ---------------------------------------------------------
# Persist resolution
# ---------------------------------------------------------

def create_auto_join_mapping(
    database: Session,
    relationship_id: int,
    auto_approve: bool = True,
) -> tuple[
    AutoJoinResolution,
    BusinessRelationshipJoinMapping
    | None,
]:

    resolution = (
        resolve_relationship_join(
            database=database,
            relationship_id=(
                relationship_id
            ),
        )
    )

    if resolution.existing_mapping:
        return (
            resolution,
            resolution.existing_mapping,
        )

    candidate = (
        resolution.candidate
    )

    if candidate is None:
        return resolution, None

    existing_exact = (
        load_exact_existing_mapping(
            database=database,
            relationship_id=(
                relationship_id
            ),
            candidate=candidate,
        )
    )

    if existing_exact:
        # Reuse the existing mapping rather than
        # attempting a duplicate INSERT.

        if (
            auto_approve
            and resolution.can_auto_approve
        ):
            existing_exact.approval_status = (
                "approved"
            )

            existing_exact.is_active = True

            existing_exact.confidence = max(
                existing_exact.confidence,
                candidate.confidence,
            )

            database.commit()

            database.refresh(
                existing_exact
            )

        resolution.status = (
            "already_resolved"
        )

        resolution.existing_mapping = (
            existing_exact
        )

        resolution.message = (
            "The resolved physical join mapping "
            "already exists and was reused."
        )

        return (
            resolution,
            existing_exact,
        )

    if (
        resolution.status
        not in {
            "auto_approvable",
            "suggested",
        }
    ):
        return resolution, None

    approval_status = "draft"

    if (
        auto_approve
        and resolution.can_auto_approve
    ):
        approval_status = "approved"

    mapping = (
        BusinessRelationshipJoinMapping(
            relationship_id=(
                relationship_id
            ),

            source_metadata_table_id=(
                candidate.source_table.id
            ),

            source_metadata_column_id=(
                candidate.source_column.id
            ),

            target_metadata_table_id=(
                candidate.target_table.id
            ),

            target_metadata_column_id=(
                candidate.target_column.id
            ),

            join_type="inner",

            description=(
                "Automatically resolved by "
                "NIBGPT Auto Join Mapper. "
                + "; ".join(
                    candidate.reasons
                )
            ),

            confidence=(
                candidate.confidence
            ),

            approval_status=(
                approval_status
            ),

            is_active=True,
        )
    )

    database.add(
        mapping
    )

    database.commit()

    database.refresh(
        mapping
    )

    return resolution, mapping