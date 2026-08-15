from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.orm import Session

from app.ai.relationship_reasoning import (
    analyze_relationship_reasoning,
)
from app.database.session import (
    get_db,
)
from app.schemas.reasoning import (
    ReasoningCapabilityResponse,
    ReasoningColumnResponse,
    ReasoningDomainResponse,
    ReasoningEntityResponse,
    ReasoningPathResponse,
    ReasoningPlanResponse,
    ReasoningRelationshipStepResponse,
    ReasoningRequest,
    ReasoningTableResponse,
)


router = APIRouter(
    prefix="/api/reasoning",
    tags=["Relationship Reasoning Engine"],
)


@router.post(
    "/analyze",
    response_model=ReasoningPlanResponse,
)
def analyze_reasoning(
    payload: ReasoningRequest,
    database: Session = Depends(
        get_db
    ),
):
    result = (
        analyze_relationship_reasoning(
            database=database,
            prompt=payload.prompt.strip(),
            requested_domain_id=(
                payload.domain_id
            ),
            maximum_entities=(
                payload.maximum_entities
            ),
            maximum_path_depth=(
                payload.maximum_path_depth
            ),
        )
    )

    domain_response = None

    domain_match = result[
        "selected_domain"
    ]

    if domain_match:
        domain_response = (
            ReasoningDomainResponse(
                id=domain_match.domain.id,
                name=domain_match.domain.name,
                description=(
                    domain_match
                    .domain
                    .description
                ),
                confidence=(
                    domain_match.confidence
                ),
                reasons=(
                    domain_match.reasons
                ),
            )
        )

    capability_responses = [
        ReasoningCapabilityResponse(
            id=match.capability.id,
            domain_id=(
                match.capability.domain_id
            ),
            name=(
                match.capability.name
            ),
            description=(
                match.capability.description
            ),
            capability_type=(
                match.capability
                .capability_type
            ),
            maturity_level=(
                match.capability
                .maturity_level
            ),
            confidence=(
                match.confidence
            ),
            reasons=match.reasons,
        )
        for match in result[
            "matched_capabilities"
        ]
    ]

    entity_responses = [
        ReasoningEntityResponse(
            id=match.entity.id,
            domain_id=(
                match.entity.domain_id
            ),
            name=match.entity.name,
            description=(
                match.entity.description
            ),
            classification=(
                match.entity
                .classification
            ),
            confidence=(
                match.confidence
            ),
            matched_terms=(
                match.matched_terms
            ),
            reasons=match.reasons,
        )
        for match in result[
            "matched_entities"
        ]
    ]

    path_responses = []

    for path in result[
        "relationship_paths"
    ]:
        path_responses.append(
            ReasoningPathResponse(
                start_entity_id=(
                    path.start_entity_id
                ),
                end_entity_id=(
                    path.end_entity_id
                ),
                steps=[
                    ReasoningRelationshipStepResponse(
                        relationship_id=(
                            step.relationship.id
                        ),
                        source_entity_id=(
                            step.source_entity.id
                        ),
                        source_entity_name=(
                            step.source_entity.name
                        ),
                        relationship_name=(
                            step.relationship_name
                        ),
                        target_entity_id=(
                            step.target_entity.id
                        ),
                        target_entity_name=(
                            step.target_entity.name
                        ),
                        confidence=(
                            step.relationship
                            .confidence
                        ),
                    )
                    for step in path.steps
                ],
                confidence=(
                    path.confidence
                ),
                explanation=(
                    path.explanation
                ),
            )
        )

    table_responses = []

    for resolved_table in result[
        "physical_tables"
    ]:
        table_responses.append(
            ReasoningTableResponse(
                id=(
                    resolved_table.table.id
                ),
                data_source_id=(
                    resolved_table
                    .table
                    .data_source_id
                ),
                schema_name=(
                    resolved_table
                    .table
                    .schema_name
                ),
                table_name=(
                    resolved_table
                    .table
                    .table_name
                ),
                business_name=(
                    resolved_table
                    .table
                    .business_name
                ),
                description=(
                    resolved_table
                    .table
                    .description
                ),
                entity_id=(
                    resolved_table.entity.id
                ),
                entity_name=(
                    resolved_table
                    .entity
                    .name
                ),
                mapping_type=(
                    resolved_table
                    .mapping_type
                ),
                mapping_confidence=(
                    resolved_table
                    .mapping_confidence
                ),
                columns=[
                    ReasoningColumnResponse(
                        id=(
                            column_match
                            .column
                            .id
                        ),
                        column_name=(
                            column_match
                            .column
                            .column_name
                        ),
                        business_name=(
                            column_match
                            .column
                            .business_name
                        ),
                        description=(
                            column_match
                            .column
                            .description
                        ),
                        data_type=(
                            column_match
                            .column
                            .data_type
                        ),
                        classification=(
                            column_match
                            .column
                            .classification
                        ),
                        is_sensitive=(
                            column_match
                            .column
                            .is_sensitive
                        ),
                        confidence=(
                            column_match
                            .confidence
                        ),
                        matched_terms=(
                            column_match
                            .matched_terms
                        ),
                    )
                    for column_match
                    in resolved_table.columns
                ],
            )
        )

    return ReasoningPlanResponse(
        prompt=result["prompt"],
        normalized_prompt=result[
            "normalized_prompt"
        ],
        intent=result["intent"],
        intent_confidence=result[
            "intent_confidence"
        ],
        selected_domain=(
            domain_response
        ),
        matched_capabilities=(
            capability_responses
        ),
        matched_entities=(
            entity_responses
        ),
        relationship_paths=(
            path_responses
        ),
        physical_tables=(
            table_responses
        ),
        overall_confidence=result[
            "overall_confidence"
        ],
        requires_clarification=result[
            "requires_clarification"
        ],
        clarification_questions=result[
            "clarification_questions"
        ],
        warnings=result["warnings"],
        explanation=result[
            "explanation"
        ],
    )
