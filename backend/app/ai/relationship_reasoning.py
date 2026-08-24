import json
import re
from collections import deque
from dataclasses import dataclass, field

from click import prompt

from sqlalchemy import select
from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.ai.entity_extractor import (
    extract_entities,
)
from app.ai.intent_detector import (
    detect_intent,
)
from app.models.business_capability import (
    BusinessCapability,
)
from app.models.business_entity import (
    BusinessDomain,
    BusinessEntity,
)
from app.models.business_relationship import (
    BusinessEntityRelationship,
)
from app.models.metadata import (
    MetadataColumn,
    MetadataTable,
)


@dataclass
class DomainMatch:
    domain: BusinessDomain
    score: int
    confidence: int
    reasons: list[str] = field(
        default_factory=list
    )


@dataclass
class CapabilityMatch:
    capability: BusinessCapability
    score: int
    confidence: int
    reasons: list[str] = field(
        default_factory=list
    )


@dataclass
class EntityMatch:
    entity: BusinessEntity
    score: int
    confidence: int
    matched_terms: list[str] = field(
        default_factory=list
    )
    reasons: list[str] = field(
        default_factory=list
    )


@dataclass
class RelationshipStep:
    relationship: BusinessEntityRelationship
    source_entity: BusinessEntity
    target_entity: BusinessEntity
    relationship_name: str


@dataclass
class RelationshipPath:
    start_entity_id: int
    end_entity_id: int
    steps: list[RelationshipStep]
    confidence: int
    explanation: str


@dataclass
class ResolvedColumn:
    column: MetadataColumn
    confidence: int
    matched_terms: list[str]


@dataclass
class ResolvedTable:
    table: MetadataTable
    entity: BusinessEntity
    mapping_type: str
    mapping_confidence: int
    columns: list[ResolvedColumn]


def normalize_text(
    value: str | None,
) -> str:
    if not value:
        return ""

    normalized = value.lower()

    normalized = re.sub(
        r"([a-z0-9])([A-Z])",
        r"\1 \2",
        normalized,
    )

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


def parse_saved_list(
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
                if normalize_text(
                    str(item)
                )
            ]

    except (
        json.JSONDecodeError,
        TypeError,
    ):
        pass

    return [
        normalize_text(item)
        for item in re.split(
            r"[,;\n]+",
            value,
        )
        if normalize_text(item)
    ]


def singularize(
    value: str,
) -> str:
    word = normalize_text(
        value
    )

    if not word:
        return word

    # --------------------------------------------------
    # Common English plural handling
    # --------------------------------------------------

    if word.endswith("ies") and len(word) > 3:
        return (
            word[:-3]
            + "y"
        )

    if word.endswith("ches"):
        return word[:-2]

    if word.endswith("shes"):
        return word[:-2]

    if word.endswith("xes"):
        return word[:-2]

    if word.endswith("zes"):
        return word[:-2]

    if word.endswith("sses"):
        return word[:-2]

    if word.endswith("ses"):
        return word[:-2]

    if (
        word.endswith("s")
        and not word.endswith("ss")
    ):
        return word[:-1]

    return word


def expand_terms(
    values: list[str],
) -> list[str]:
    terms: list[str] = []

    for value in values:
        normalized = normalize_text(value)

        if not normalized:
            continue

        terms.append(normalized)

        singular = singularize(
            normalized
        )

        if singular != normalized:
            terms.append(singular)

    return list(
        dict.fromkeys(terms)
    )



# Generic query words must never identify a business entity.
# Status, aggregation and time expressions are also removed separately
# when build_entity_terms() is called.
ENTITY_QUERY_STOPWORDS = {
    "show",
    "display",
    "list",
    "give",
    "get",
    "find",
    "report",
    "reports",
    "reporting",
    "all",
    "the",
    "a",
    "an",
    "of",
    "for",
    "with",
    "without",
    "and",
    "or",
    "by",
    "from",
    "to",
    "in",
    "on",
    "at",
    "as",
    "whose",
    "which",
    "who",
    "what",
    "when",
    "where",
    "how",
    "this",
    "that",
    "these",
    "those",
    "top",
    "bottom",
    "first",
    "last",
}


def build_entity_terms(
    extraction_result: dict,
) -> list[str]:
    """
    Build terms that are safe to use for business-entity identification.

    Entity ranking should use business nouns/concepts only. Filter words
    such as 'active', aggregation words such as 'total', and time phrases
    such as 'this month' must not cause unrelated entities to match.
    """
    keyword_terms = expand_terms(
        extraction_result.get(
            "keywords",
            [],
        )
    )

    excluded_values: list[str] = []

    excluded_values.extend(
        extraction_result.get(
            "status_terms",
            [],
        )
    )

    excluded_values.extend(
        extraction_result.get(
            "aggregation_terms",
            [],
        )
    )

    excluded_values.extend(
        extraction_result.get(
            "time_expressions",
            [],
        )
    )

    excluded_terms = set(
        expand_terms(
            excluded_values
        )
    )

    cleaned_terms: list[str] = []

    for term in keyword_terms:
        normalized = normalize_text(
            term
        )

        if not normalized:
            continue

        if (
            normalized
            in ENTITY_QUERY_STOPWORDS
        ):
            continue

        if normalized in excluded_terms:
            continue

        # Remove individual excluded/stop words from multi-word terms
        # while preserving real business phrases.
        words = [
            word
            for word
            in normalized.split()
            if (
                word
                not in ENTITY_QUERY_STOPWORDS
                and word
                not in excluded_terms
            )
        ]

        cleaned = " ".join(
            words
        ).strip()

        if cleaned:
            cleaned_terms.append(
                cleaned
            )

            singular = singularize(
                cleaned
            )

            if singular != cleaned:
                cleaned_terms.append(
                    singular
                )

    return list(
        dict.fromkeys(
            cleaned_terms
        )
    )


def text_match_score(
    search_terms: list[str],
    value: str | None,
    exact_score: int,
    partial_score: int,
) -> tuple[int, list[str]]:
    normalized_value = normalize_text(
        value
    )

    if not normalized_value:
        return 0, []

    score = 0
    matches: list[str] = []

    for term in search_terms:
        if not term:
            continue

        if term == normalized_value:
            score += exact_score
            matches.append(term)

        elif (
            f" {term} "
            in f" {normalized_value} "
        ):
            score += partial_score
            matches.append(term)

        elif term in normalized_value:
            score += max(
                1,
                partial_score // 2,
            )
            matches.append(term)

    return (
        score,
        list(dict.fromkeys(matches)),
    )


def score_to_confidence(
    score: int,
) -> int:
    if score >= 260:
        return 99

    if score >= 200:
        return 96

    if score >= 150:
        return 92

    if score >= 110:
        return 86

    if score >= 75:
        return 78

    if score >= 45:
        return 67

    if score >= 20:
        return 52

    return 35


def load_domains(
    database: Session,
) -> list[BusinessDomain]:
    statement = (
        select(BusinessDomain)
        .where(
            BusinessDomain.is_active.is_(
                True
            )
        )
        .order_by(
            BusinessDomain.name
        )
    )

    return list(
        database.scalars(
            statement
        ).all()
    )


def load_capabilities(
    database: Session,
    domain_id: int | None,
) -> list[BusinessCapability]:
    statement = (
        select(BusinessCapability)
        .options(
            selectinload(
                BusinessCapability
                .entity_mappings
            )
        )
        .where(
            BusinessCapability
            .is_active
            .is_(True),
            BusinessCapability
            .approval_status
            == "approved",
        )
    )

    if domain_id is not None:
        statement = statement.where(
            BusinessCapability.domain_id
            == domain_id
        )

    return list(
        database.scalars(
            statement
        ).unique().all()
    )


def load_entities(
    database: Session,
    domain_id: int | None,
) -> list[BusinessEntity]:
    statement = (
        select(BusinessEntity)
        .options(
            selectinload(
                BusinessEntity
                .table_mappings
            )
        )
        .where(
            BusinessEntity.is_active.is_(
                True
            ),
            BusinessEntity
            .approval_status
            == "approved",
            BusinessEntity
            .ai_access_allowed
            .is_(True),
        )
    )

    if domain_id is not None:
        statement = statement.where(
            BusinessEntity.domain_id
            == domain_id
        )

    return list(
        database.scalars(
            statement
        ).unique().all()
    )


def load_relationships(
    database: Session,
) -> list[
    BusinessEntityRelationship
]:
    statement = (
        select(
            BusinessEntityRelationship
        )
        .options(
            selectinload(
                BusinessEntityRelationship
                .source_entity
            ),
            selectinload(
                BusinessEntityRelationship
                .target_entity
            ),
        )
        .where(
            BusinessEntityRelationship
            .is_active
            .is_(True),
            BusinessEntityRelationship
            .approval_status
            == "approved",
        )
    )

    return list(
        database.scalars(
            statement
        ).unique().all()
    )


def rank_domains(
    prompt: str,
    terms: list[str],
    domains: list[BusinessDomain],
    requested_domain_id: int | None,
) -> list[DomainMatch]:
    matches: list[DomainMatch] = []

    for domain in domains:
        score = 0
        reasons: list[str] = []

        name_score, _ = text_match_score(
            terms,
            domain.name,
            110,
            45,
        )

        if name_score:
            score += name_score
            reasons.append(
                "Business domain name matched."
            )

        description_score, _ = (
            text_match_score(
                terms,
                domain.description,
                45,
                18,
            )
        )

        if description_score:
            score += description_score
            reasons.append(
                "Business domain description matched."
            )

        department_score, _ = (
            text_match_score(
                terms,
                domain.department,
                35,
                14,
            )
        )

        if department_score:
            score += department_score
            reasons.append(
                "Department matched."
            )

        if (
            requested_domain_id
            == domain.id
        ):
            score += 180
            reasons.append(
                "The user explicitly selected this domain."
            )

        if score <= 0:
            continue

        matches.append(
            DomainMatch(
                domain=domain,
                score=score,
                confidence=(
                    score_to_confidence(
                        score
                    )
                ),
                reasons=reasons,
            )
        )

    matches.sort(
        key=lambda item: item.score,
        reverse=True,
    )

    return matches


def rank_capabilities(
    terms: list[str],
    capabilities: list[
        BusinessCapability
    ],
    entity_matches: list[
        EntityMatch
    ] | None = None,
) -> list[CapabilityMatch]:
    entity_ids = {
        match.entity.id
        for match in (
            entity_matches or []
        )
    }

    matches: list[
        CapabilityMatch
    ] = []

    for capability in capabilities:
        score = 0
        reasons: list[str] = []

        name_score, _ = text_match_score(
            terms,
            capability.name,
            100,
            40,
        )

        if name_score:
            score += name_score
            reasons.append(
                "Capability name matched."
            )

        description_score, _ = (
            text_match_score(
                terms,
                capability.description,
                50,
                18,
            )
        )

        if description_score:
            score += description_score
            reasons.append(
                "Capability description matched."
            )

        mapped_ids = {
            mapping.business_entity_id
            for mapping
            in capability.entity_mappings
            if mapping.is_active
        }

        overlapping_entities = (
            mapped_ids & entity_ids
        )

        if overlapping_entities:
            score += (
                len(
                    overlapping_entities
                )
                * 50
            )

            reasons.append(
                f"{len(overlapping_entities)} matched "
                "business entity or entities belong "
                "to this capability."
            )

        # Do not select a capability merely because it has
        # a strong maturity level. It must first match the
        # prompt or contain a matched business entity.
        if score <= 0:
            continue

        if capability.maturity_level in {
            "managed",
            "optimized",
        }:
            score += 8
            reasons.append(
                "Capability maturity is strong."
            )

        matches.append(
            CapabilityMatch(
                capability=capability,
                score=score,
                confidence=(
                    score_to_confidence(
                        score
                    )
                ),
                reasons=list(
                    dict.fromkeys(
                        reasons
                    )
                ),
            )
        )

    matches.sort(
        key=lambda item: item.score,
        reverse=True,
    )

    return matches

def rank_entities(
    terms: list[str],
    entities: list[BusinessEntity],
    maximum_entities: int,
) -> list[EntityMatch]:
    matches: list[EntityMatch] = []

    for entity in entities:
        score = 0
        reasons: list[str] = []
        matched_terms: list[str] = []

        # Entity name is strongest evidence.
        name_score, name_matches = (
            text_match_score(
                terms,
                entity.name,
                150,
                60,
            )
        )

        if name_score:
            score += name_score

            reasons.append(
                "Business entity name matched."
            )

            matched_terms.extend(
                name_matches
            )

        # Synonyms are strong evidence, but not as
        # strong as the real business entity name.
        for synonym in parse_saved_list(
            entity.synonyms
        ):
            (
                synonym_score,
                synonym_matches,
            ) = text_match_score(
                terms,
                synonym,
                115,
                45,
            )

            if synonym_score:
                score += synonym_score

                reasons.append(
                    "Business synonym matched."
                )

                matched_terms.extend(
                    synonym_matches
                )

        # Description is supporting evidence only.
        description_score, description_matches = (
            text_match_score(
                terms,
                entity.description,
                35,
                12,
            )
        )

        if description_score:
            score += description_score

            reasons.append(
                "Business entity description matched."
            )

            matched_terms.extend(
                description_matches
            )

        # Business owner is very weak supporting evidence.
        owner_score, owner_matches = (
            text_match_score(
                terms,
                entity.business_owner,
                15,
                5,
            )
        )

        if owner_score:
            score += owner_score

            reasons.append(
                "Business owner matched."
            )

            matched_terms.extend(
                owner_matches
            )

        # Absolutely no semantic evidence.
        if score <= 0:
            continue

        # Physical mapping must NEVER make an entity
        # a match by itself.
        if entity.table_mappings:
            score += 8

            reasons.append(
                "The entity has physical data mappings."
            )

        matches.append(
            EntityMatch(
                entity=entity,
                score=score,
                confidence=(
                    score_to_confidence(
                        score
                    )
                ),
                matched_terms=list(
                    dict.fromkeys(
                        matched_terms
                    )
                ),
                reasons=list(
                    dict.fromkeys(
                        reasons
                    )
                ),
            )
        )

    matches.sort(
        key=lambda item: item.score,
        reverse=True,
    )

    return matches[
        :maximum_entities
    ]


def entity_explicitly_mentioned(
    prompt: str,
    entity: BusinessEntity,
) -> bool:
    """
    Return True only when the entity name or one of its
    approved synonyms is explicitly present in the prompt.

    Examples:

    'Show active vehicles'
        Vehicles -> True
        Maintenance -> False
        Bolo -> False

    'Show vehicles under maintenance'
        Vehicles -> True
        Maintenance -> True
    """

    normalized_prompt = (
        normalize_text(prompt)
    )

    prompt_words = set(
        normalized_prompt.split()
    )

    candidates: list[str] = [
        entity.name,
    ]

    candidates.extend(
        parse_saved_list(
            entity.synonyms
        )
    )

    for candidate in candidates:
        normalized_candidate = (
            normalize_text(candidate)
        )

        if not normalized_candidate:
            continue

        # Exact multi-word phrase.
        if (
            f" {normalized_candidate} "
            in f" {normalized_prompt} "
        ):
            return True

        candidate_words = (
            normalized_candidate.split()
        )

        # Single-word entity.
        if len(candidate_words) == 1:
            candidate_word = (
                candidate_words[0]
            )

            singular_candidate = singularize(
                candidate_word
            )

            for prompt_word in prompt_words:
                if (
                    prompt_word
                    == candidate_word
                    or singularize(
                        prompt_word
                    )
                    == singular_candidate
                ):
                    return True

    return False


def prune_entity_matches(
    prompt: str,
    matches: list[EntityMatch],
) -> list[EntityMatch]:
    """
    Preserve the strongest business entity together
    with explicitly requested business dimensions.

    Examples:

    "Show total deposit balance by branch"
        -> Fbnk Account + F Company

    "Show total deposit balance by district"
        -> Fbnk Account + Districts

    "Show total deposit balance by customer"
        -> Fbnk Account + Fbnk Customer

    "Show total deposit balance by currency"
        -> Fbnk Account only
    """

    if not matches:
        return []

    normalized_prompt = normalize_text(
        prompt
    )

    selected: list[
        EntityMatch
    ] = []

    strongest = matches[0]

    # Always preserve the strongest semantic entity.
    selected.append(
        strongest
    )

    # --------------------------------------------------
    # Explicit business dimensions
    # --------------------------------------------------

    dimension_terms = {
        "branch": {
            "f company",
        },
        "branches": {
            "f company",
        },
        "district": {
            "districts",
            "f eb district",
        },
        "districts": {
            "districts",
            "f eb district",
        },
        "customer": {
            "fbnk customer",
        },
        "customers": {
            "fbnk customer",
        },
    }

    requested_dimensions: set[str] = set()

        # --------------------------------------------------
    # Rich branch account reports also require District.
    #
    # Example:
    #
    # "Show active account report by branch"
    #
    # Required entities:
    # Fbnk Account
    # F Company
    # Districts
    # --------------------------------------------------

    if (
        "account report"
        in normalized_prompt
        and (
            "by branch"
            in normalized_prompt
            or "by branches"
            in normalized_prompt
        )
    ):
        requested_dimensions.update(
            {
                "districts",
                "f eb district",
            }
        )

    for term, entity_names in (
        dimension_terms.items()
    ):
        if (
            f" {term} "
            in f" {normalized_prompt} "
        ):
            requested_dimensions.update(
                entity_names
            )

    # --------------------------------------------------
    # Preserve requested dimension entities.
    # --------------------------------------------------

    for match in matches[1:]:
        entity_name = normalize_text(
            match.entity.name
        )

        if (
            entity_name
            in requested_dimensions
        ):
            selected.append(
                match
            )

    # --------------------------------------------------
    # Preserve other explicitly named entities.
    # --------------------------------------------------

    for match in matches[1:]:
        if match in selected:
            continue

        if entity_explicitly_mentioned(
            prompt,
            match.entity,
        ):
            selected.append(
                match
            )

    return selected

def build_relationship_graph(
    relationships: list[
        BusinessEntityRelationship
    ],
) -> dict[
    int,
    list[
        tuple[
            int,
            BusinessEntityRelationship,
            bool,
        ]
    ],
]:
    graph: dict[
        int,
        list[
            tuple[
                int,
                BusinessEntityRelationship,
                bool,
            ]
        ],
    ] = {}

    for relationship in relationships:
        graph.setdefault(
            relationship.source_entity_id,
            [],
        ).append(
            (
                relationship.target_entity_id,
                relationship,
                True,
            )
        )

        graph.setdefault(
            relationship.target_entity_id,
            [],
        ).append(
            (
                relationship.source_entity_id,
                relationship,
                False,
            )
        )

    return graph


def find_relationship_path(
    start_entity_id: int,
    end_entity_id: int,
    graph: dict,
    entity_lookup: dict[
        int,
        BusinessEntity,
    ],
    maximum_depth: int,
) -> RelationshipPath | None:
    queue = deque(
        [
            (
                start_entity_id,
                [],
            )
        ]
    )

    visited = {
        start_entity_id
    }

    while queue:
        (
            current_entity_id,
            current_steps,
        ) = queue.popleft()

        if (
            len(current_steps)
            >= maximum_depth
        ):
            continue

        for (
            next_entity_id,
            relationship,
            forward,
        ) in graph.get(
            current_entity_id,
            [],
        ):
            if next_entity_id in visited:
                continue

            current_entity = (
                entity_lookup.get(
                    current_entity_id
                )
            )

            next_entity = (
                entity_lookup.get(
                    next_entity_id
                )
            )

            if (
                current_entity is None
                or next_entity is None
            ):
                continue

            relationship_name = (
                relationship
                .relationship_name
                if forward
                else (
                    relationship
                    .inverse_relationship_name
                    or relationship
                    .relationship_name
                )
            )

            step = RelationshipStep(
                relationship=relationship,
                source_entity=current_entity,
                target_entity=next_entity,
                relationship_name=(
                    relationship_name
                ),
            )

            new_steps = [
                *current_steps,
                step,
            ]

            if (
                next_entity_id
                == end_entity_id
            ):
                step_confidences = [
                    item.relationship
                    .confidence
                    for item in new_steps
                ]

                path_confidence = round(
                    sum(
                        step_confidences
                    )
                    / len(
                        step_confidences
                    )
                )

                explanation = " → ".join(
                    [
                        new_steps[0]
                        .source_entity
                        .name,
                        *[
                            (
                                f"{item.relationship_name} "
                                f"{item.target_entity.name}"
                            )
                            for item
                            in new_steps
                        ],
                    ]
                )

                return RelationshipPath(
                    start_entity_id=(
                        start_entity_id
                    ),
                    end_entity_id=(
                        end_entity_id
                    ),
                    steps=new_steps,
                    confidence=(
                        path_confidence
                    ),
                    explanation=(
                        explanation
                    ),
                )

            visited.add(
                next_entity_id
            )

            queue.append(
                (
                    next_entity_id,
                    new_steps,
                )
            )

    return None


def discover_paths(
    entity_matches: list[
        EntityMatch
    ],
    relationships: list[
        BusinessEntityRelationship
    ],
    all_entities: list[
        BusinessEntity
    ],
    maximum_depth: int,
) -> list[RelationshipPath]:
    if len(entity_matches) < 2:
        return []

    graph = build_relationship_graph(
        relationships
    )

    entity_lookup = {
        entity.id: entity
        for entity in all_entities
    }

    paths: list[
        RelationshipPath
    ] = []

    matched_entity_ids = [
        match.entity.id
        for match in entity_matches
    ]

    for source_index in range(
        len(matched_entity_ids)
    ):
        for target_index in range(
            source_index + 1,
            len(matched_entity_ids),
        ):
            path = find_relationship_path(
                start_entity_id=(
                    matched_entity_ids[
                        source_index
                    ]
                ),
                end_entity_id=(
                    matched_entity_ids[
                        target_index
                    ]
                ),
                graph=graph,
                entity_lookup=(
                    entity_lookup
                ),
                maximum_depth=(
                    maximum_depth
                ),
            )

            if path:
                paths.append(path)

    paths.sort(
        key=lambda item: (
            len(item.steps),
            -item.confidence,
        )
    )

    return paths


def score_column(
    column: MetadataColumn,
    terms: list[str],
) -> ResolvedColumn | None:
    score = 0
    matched_terms: list[str] = []

    fields = [
        (
            column.business_name,
            80,
            28,
        ),
        (
            column.column_name,
            65,
            24,
        ),
        (
            column.description,
            40,
            15,
        ),
    ]

    for (
        value,
        exact_score,
        partial_score,
    ) in fields:
        (
            field_score,
            field_matches,
        ) = text_match_score(
            terms,
            value,
            exact_score,
            partial_score,
        )

        score += field_score

        matched_terms.extend(
            field_matches
        )

    for synonym in parse_saved_list(
        column.synonyms
    ):
        (
            synonym_score,
            synonym_matches,
        ) = text_match_score(
            terms,
            synonym,
            70,
            26,
        )

        score += synonym_score

        matched_terms.extend(
            synonym_matches
        )

    if score <= 0:
        return None

# A primary key may strengthen an existing semantic match,
# but it must never become relevant by itself.
    if column.is_primary_key:
        score += 8

    return ResolvedColumn(
        column=column,
        confidence=(
            score_to_confidence(
                score
            )
        ),
        matched_terms=list(
            dict.fromkeys(
                matched_terms
            )
        ),
    )


def resolve_physical_tables(
    database: Session,
    entity_matches: list[
        EntityMatch
    ],
    terms: list[str],
) -> list[ResolvedTable]:
    resolved: list[
        ResolvedTable
    ] = []

    for entity_match in entity_matches:
        entity = entity_match.entity

        active_mappings = [
            mapping
            for mapping
            in entity.table_mappings
            if mapping.is_active
        ]

        if not active_mappings:
            continue

        primary_mappings = [
            mapping
            for mapping
            in active_mappings
            if mapping.mapping_type
            == "primary"
        ]

        if primary_mappings:
            entity_name = normalize_text(
                entity.name
            )

            scored_primary_mappings = []

            for mapping in primary_mappings:
                table = database.get(
                    MetadataTable,
                    mapping.metadata_table_id,
                )

                if table is None:
                    continue

                table_business_name = (
                    normalize_text(
                        table.business_name
                    )
                )

                table_name = normalize_text(
                    table.table_name
                )

                score = 0

                if (
                    table_business_name
                    == entity_name
                ):
                    score += 200

                if (
                    entity_name
                    in table_business_name
                ):
                    score += 100

                if (
                    entity_name
                    in table_name
                ):
                    score += 80

                singular_entity = singularize(
                    entity_name
                )

                if (
                    singular_entity
                    and singular_entity
                    in table_name
                ):
                    score += 70

                score += mapping.confidence

                scored_primary_mappings.append(
                    (
                        score,
                        mapping,
                    )
                )

            scored_primary_mappings.sort(
                key=lambda item: item[0],
                reverse=True,
            )

            mappings_to_resolve = (
                [
                    scored_primary_mappings[
                        0
                    ][1]
                ]
                if scored_primary_mappings
                else primary_mappings[:1]
            )

        else:
            mappings_to_resolve = (
                active_mappings[:1]
            )

        for mapping in mappings_to_resolve:
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

            if table is None:
                continue

            if (
                not table.is_discovered
                or not table.is_enabled
                or not table.ai_access_allowed
            ):
                continue

            column_matches: list[
                ResolvedColumn
            ] = []

            for column in table.columns:
                if (
                    not column.is_discovered
                    or not column.is_enabled
                    or not column.ai_access_allowed
                ):
                    continue

                result = score_column(
                    column,
                    terms,
                )

                if result:
                    column_matches.append(
                        result
                    )

            column_matches.sort(
                key=lambda item:
                    item.confidence,
                reverse=True,
            )

            resolved.append(
                ResolvedTable(
                    table=table,
                    entity=entity,
                    mapping_type=(
                        mapping.mapping_type
                    ),
                    mapping_confidence=(
                        mapping.confidence
                    ),
                    columns=(
                        column_matches[:12]
                    ),
                )
            )

    return resolved


def calculate_overall_confidence(
    intent_confidence: int,
    domain_match: (
        DomainMatch | None
    ),
    capability_matches: list[
        CapabilityMatch
    ],
    entity_matches: list[
        EntityMatch
    ],
    paths: list[
        RelationshipPath
    ],
    physical_tables: list[
        ResolvedTable
    ],
) -> int:
    components: list[int] = [
        intent_confidence
    ]

    if domain_match:
        components.append(
            domain_match.confidence
        )

    if capability_matches:
        components.append(
            capability_matches[
                0
            ].confidence
        )

    if entity_matches:
        components.append(
            round(
                sum(
                    item.confidence
                    for item
                    in entity_matches
                )
                / len(
                    entity_matches
                )
            )
        )

    if paths:
        components.append(
            round(
                sum(
                    path.confidence
                    for path in paths
                )
                / len(paths)
            )
        )

    if physical_tables:
        components.append(
            round(
                sum(
                    table
                    .mapping_confidence
                    for table
                    in physical_tables
                )
                / len(
                    physical_tables
                )
            )
        )

    return round(
        sum(components)
        / len(components)
    )


def analyze_relationship_reasoning(
    database: Session,
    prompt: str,
    requested_domain_id: int | None,
    maximum_entities: int,
    maximum_path_depth: int,
) -> dict:
    intent_result = detect_intent(
        prompt
    )

    extraction_result = (
        extract_entities(prompt)
    )

    normalized_prompt = (
        extraction_result[
            "normalized_prompt"
        ]
    )

    # Entity/domain/capability matching must be driven by
    # business concepts, not status/filter/aggregation words.
    entity_terms = build_entity_terms(
        extraction_result
    )

    # --------------------------------------------------
    # Rich account-report semantic expansion
    #
    # A branch account report also includes the
    # related District Name as a report dimension.
    # --------------------------------------------------

    normalized_business_prompt = normalize_text(
                prompt
            )

    if (
            "account report"
            in normalized_business_prompt
            and (
                "by branch"
                in normalized_business_prompt
                or "by branches"
                in normalized_business_prompt
            )
        ):
        entity_terms.extend(
        [
            "district",
            "districts",
        ]
    )

    entity_terms = list(
        dict.fromkeys(
            entity_terms
        )
    )

    # Broader context is still useful for physical-column
    # resolution because status, date and aggregation words
    # often identify the required columns.
    context_terms = expand_terms(
        extraction_result.get(
            "keywords",
            [],
        )
        + extraction_result.get(
            "status_terms",
            [],
        )
        + extraction_result.get(
            "aggregation_terms",
            [],
        )
        + extraction_result.get(
            "time_expressions",
            [],
        )
    )

    warnings: list[str] = []
    explanation: list[str] = []
    clarification_questions: list[
        str
    ] = []

    if not intent_result.is_safe:
        return {
            "prompt": prompt,
            "normalized_prompt": (
                normalized_prompt
            ),
            "intent": (
                intent_result.intent
            ),
            "intent_confidence": (
                intent_result.confidence
            ),
            "selected_domain": None,
            "matched_capabilities": [],
            "matched_entities": [],
            "relationship_paths": [],
            "physical_tables": [],
            "overall_confidence": 0,
            "requires_clarification": False,
            "clarification_questions": [],
            "warnings": [
                intent_result
                .blocked_reason
                or (
                    "The request violates "
                    "the read-only policy."
                )
            ],
            "explanation": [
                (
                    "Reasoning stopped because "
                    "the request is not read-only."
                )
            ],
        }

    domains = load_domains(
        database
    )

    # Domain resolution should use semantic/business terms.
    # An explicit domain selection still receives the strong
    # requested-domain bonus inside rank_domains().
    domain_matches = rank_domains(
        prompt=prompt,
        terms=entity_terms,
        domains=domains,
        requested_domain_id=(
            requested_domain_id
        ),
    )

    selected_domain_match = (
        domain_matches[0]
        if domain_matches
        else None
    )

    selected_domain_id = (
        selected_domain_match
        .domain.id
        if selected_domain_match
        else requested_domain_id
    )

    all_entities = load_entities(
        database=database,
        domain_id=(
            selected_domain_id
        ),
    )

    entity_matches = rank_entities(
    terms=entity_terms,
    entities=all_entities,
    maximum_entities=(
        maximum_entities
    ),
    )

    entity_matches = prune_entity_matches(
    prompt=prompt,
    matches=entity_matches,
)

    capabilities = load_capabilities(
        database=database,
        domain_id=(
            selected_domain_id
        ),
    )

    capability_matches = (
        rank_capabilities(
            terms=entity_terms,
            capabilities=capabilities,
            entity_matches=(
                entity_matches
            ),
        )
    )

    relationships = (
        load_relationships(
            database
        )
    )

    paths = discover_paths(
        entity_matches=entity_matches,
        relationships=relationships,
        all_entities=all_entities,
        maximum_depth=(
            maximum_path_depth
        ),
    )

    physical_tables = (
        resolve_physical_tables(
            database=database,
            entity_matches=(
                entity_matches
            ),
            terms=context_terms,
        )
    )

    overall_confidence = (
        calculate_overall_confidence(
            intent_confidence=(
                intent_result.confidence
            ),
            domain_match=(
                selected_domain_match
            ),
            capability_matches=(
                capability_matches
            ),
            entity_matches=(
                entity_matches
            ),
            paths=paths,
            physical_tables=(
                physical_tables
            ),
        )
    )

    if selected_domain_match:
        explanation.append(
            (
                "Selected business domain: "
                f"{selected_domain_match.domain.name} "
                f"({selected_domain_match.confidence}% confidence)."
            )
        )
    else:
        warnings.append(
            "No approved business domain matched the question."
        )

    if capability_matches:
        explanation.append(
            (
                "Strongest capability match: "
                f"{capability_matches[0].capability.name} "
                f"({capability_matches[0].confidence}% confidence)."
            )
        )
    else:
        warnings.append(
            "No approved business capability matched the question."
        )

    if entity_matches:
        explanation.append(
            (
                "Matched business entities: "
                + ", ".join(
                    match.entity.name
                    for match
                    in entity_matches
                )
                + "."
            )
        )
    else:
        warnings.append(
            "No approved business entity matched the question."
        )

    if paths:
        explanation.append(
            (
                f"Found {len(paths)} approved "
                "relationship path or paths."
            )
        )

    elif len(entity_matches) > 1:
        warnings.append(
            (
                "Multiple business entities matched, "
                "but no approved relationship path "
                "connects them."
            )
        )

    if not physical_tables:
        warnings.append(
            (
                "No usable physical table mappings "
                "were found for the matched entities."
            )
        )

    requires_clarification = (
        overall_confidence < 75
        or not entity_matches
        or not physical_tables
    )

    if (
        len(domain_matches) > 1
        and (
            domain_matches[0].confidence
            - domain_matches[1].confidence
            < 8
        )
    ):
        requires_clarification = True

        clarification_questions.append(
            (
                "Which business domain did you mean: "
                f"{domain_matches[0].domain.name} "
                f"or {domain_matches[1].domain.name}?"
            )
        )

    if (
    len(capability_matches) > 1
    and (
        capability_matches[0].confidence
        - capability_matches[1].confidence
        < 8
    )
    ):
        if (
        not entity_matches
        or (
            len(entity_matches) > 1
            and not paths
        )
    ):
            requires_clarification = True

        clarification_questions.append(
            (
                "Which business capability did you mean: "
                f"{capability_matches[0].capability.name} "
                f"or {capability_matches[1].capability.name}?"
            )
        )

    if not entity_matches:
        clarification_questions.append(
            (
                "Which business concept or record "
                "would you like to report on?"
            )
        )

    elif (
        len(entity_matches) > 1
        and not paths
    ):
        clarification_questions.append(
            (
                "The selected business concepts are "
                "not connected by an approved relationship. "
                "Which concept should be the primary subject?"
            )
        )

    return {
        "prompt": prompt,
        "normalized_prompt": (
            normalized_prompt
        ),
        "intent": (
            intent_result.intent
        ),
        "intent_confidence": (
            intent_result.confidence
        ),
        "selected_domain": (
            selected_domain_match
        ),
        "matched_capabilities": (
            capability_matches[:5]
        ),
        "matched_entities": (
            entity_matches
        ),
        "relationship_paths": (
            paths[:10]
        ),
        "physical_tables": (
            physical_tables
        ),
        "overall_confidence": (
            overall_confidence
        ),
        "requires_clarification": (
            requires_clarification
        ),
        "clarification_questions": (
            clarification_questions
        ),
        "warnings": warnings,
        "explanation": explanation,
    }
