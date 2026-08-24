
from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.orm import Session

from app.ai.governed_query_planner import (
    create_governed_query_plan,
)

from app.database.session import get_db
from app.schemas.governed_query_plan import (
    GovernanceCheckResponse,
    GovernedPlanAggregationResponse,
    GovernedPlanCapabilityResponse,
    GovernedPlanColumnResponse,
    GovernedPlanDomainResponse,
    GovernedPlanEntityResponse,
    GovernedPlanFilterResponse,
    GovernedPlanGroupingResponse,
    GovernedPlanSortResponse,
    GovernedPlanTableResponse,
    GovernedQueryPlanRequest,
    GovernedQueryPlanResponse,
    GovernedSemanticJoinResponse,
)


router = APIRouter(
    prefix="/api/governed-query-plan",
    tags=["Governed Query Planner"],
)


@router.post(
    "/generate",
    response_model=GovernedQueryPlanResponse,
)
def generate_governed_query_plan(
    payload: GovernedQueryPlanRequest,
    database: Session = Depends(
        get_db
    ),
):
    plan = create_governed_query_plan(
        database=database,
        prompt=payload.prompt.strip(),
        domain_id=payload.domain_id,
        requested_limit=(
            payload.requested_limit
        ),
        maximum_entities=(
            payload.maximum_entities
        ),
        maximum_path_depth=(
            payload.maximum_path_depth
        ),
        user_role=(
            payload.user_role
        ),
    )

    reasoning = (
        plan.reasoning_result
    )

    domain_response = None

    domain_match = reasoning[
        "selected_domain"
    ]

    if domain_match:
        domain_response = (
            GovernedPlanDomainResponse(
                id=domain_match.domain.id,
                name=domain_match.domain.name,
                confidence=(
                    domain_match.confidence
                ),
            )
        )

    capability_responses = [
        GovernedPlanCapabilityResponse(
            id=match.capability.id,
            name=match.capability.name,
            confidence=(
                match.confidence
            ),
        )
        for match in reasoning[
            "matched_capabilities"
        ]
    ]

    entity_responses = [
        GovernedPlanEntityResponse(
            id=match.entity.id,
            name=match.entity.name,
            classification=(
                match.entity
                .classification
            ),
            confidence=(
                match.confidence
            ),
        )
        for match in reasoning[
            "matched_entities"
        ]
    ]

    table_responses = [
        GovernedPlanTableResponse(
            metadata_table_id=(
                item.table.id
            ),
            data_source_id=(
                item.table.data_source_id
            ),
            schema_name=(
                item.table.schema_name
            ),
            table_name=(
                item.table.table_name
            ),
            business_name=(
                item.table.business_name
            ),
            entity_id=(
                item.entity.id
            ),
            entity_name=(
                item.entity.name
            ),
            mapping_type=(
                item.mapping_type
            ),
            mapping_confidence=(
                item.mapping_confidence
            ),
        )
        for item in reasoning[
            "physical_tables"
        ]
    ]

    selected_columns = [
        GovernedPlanColumnResponse(
            metadata_column_id=(
                item.resolved_column
                .column.id
            ),
            metadata_table_id=(
                item.table.table.id
            ),
            column_name=(
                item.resolved_column
                .column.column_name
            ),
            business_name=(
                item.resolved_column
                .column.business_name
            ),
            data_type=(
                item.resolved_column
                .column.data_type
            ),
            classification=(
                item.resolved_column
                .column.classification
            ),
            is_sensitive=(
                item.resolved_column
                .column.is_sensitive
            ),
            purpose=item.purpose,
            confidence=(
                item.confidence
            ),
        )
        for item in plan.selected_columns
    ]

    filters = [
        GovernedPlanFilterResponse(
            metadata_column_id=(
                item.resolved_column
                .column.id
            ),
            metadata_table_id=(
                item.table.table.id
            ),
            column_name=(
                item.resolved_column
                .column.column_name
            ),
            business_name=(
                item.resolved_column
                .column.business_name
            ),
            operator=item.operator,
            value=item.value,
            confidence=(
                item.confidence
            ),
            reason=item.reason,
        )
        for item in plan.filters
    ]

    aggregation_responses = []

    effective_aggregations = (
        plan.aggregations
        if plan.aggregations
        else (
            [plan.aggregation]
            if plan.aggregation
            else []
        )
    )

    for aggregation in effective_aggregations:
        aggregation_responses.append(
            GovernedPlanAggregationResponse(
                function=(
                    aggregation.function
                ),
                metadata_column_id=(
                    aggregation
                    .resolved_column
                    .column.id
                    if aggregation.resolved_column
                    else None
                ),
                metadata_table_id=(
                    aggregation
                    .table.table.id
                    if aggregation.table
                    else None
                ),
                column_name=(
                    aggregation
                    .resolved_column
                    .column.column_name
                    if aggregation.resolved_column
                    else None
                ),
                alias=(
                    aggregation.alias
                ),
                confidence=(
                    aggregation.confidence
                ),
            )
        )

    if plan.aggregation:
        aggregation_response = (
            GovernedPlanAggregationResponse(
                function=(
                    plan.aggregation
                    .function
                ),
                metadata_column_id=(
                    plan.aggregation
                    .resolved_column
                    .column.id
                    if (
                        plan.aggregation
                        .resolved_column
                    )
                    else None
                ),
                metadata_table_id=(
                    plan.aggregation
                    .table.table.id
                    if (
                        plan.aggregation
                        .table
                    )
                    else None
                ),
                column_name=(
                    plan.aggregation
                    .resolved_column
                    .column.column_name
                    if (
                        plan.aggregation
                        .resolved_column
                    )
                    else None
                ),
                alias=(
                    plan.aggregation.alias
                ),
                confidence=(
                    plan.aggregation
                    .confidence
                ),
            )
        )

    group_by = [
        GovernedPlanGroupingResponse(
            metadata_column_id=(
                item.resolved_column
                .column.id
            ),
            metadata_table_id=(
                item.table.table.id
            ),
            column_name=(
                item.resolved_column
                .column.column_name
            ),
            business_name=(
                item.resolved_column
                .column.business_name
            ),
            confidence=(
                item.confidence
            ),
        )
        for item in plan.group_by
    ]

    order_by = [
        GovernedPlanSortResponse(
            metadata_column_id=(
                item.resolved_column
                .column.id
            ),
            metadata_table_id=(
                item.table.table.id
            ),
            column_name=(
                item.resolved_column
                .column.column_name
            ),
            direction=item.direction,
            confidence=(
                item.confidence
            ),
        )
        for item in plan.order_by
    ]

    semantic_joins = []

    seen_relationship_ids: set[int] = set()

    for path in reasoning[
        "relationship_paths"
    ]:
        for step in path.steps:
            relationship_id = (
                step.relationship.id
            )

            if relationship_id in seen_relationship_ids:
                continue

            seen_relationship_ids.add(
                relationship_id
            )

            join_mapping = (
                plan.join_mappings.get(
                    relationship_id
                )
            )

            semantic_joins.append(
                GovernedSemanticJoinResponse(
                    relationship_id=(
                        relationship_id
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
                        step.relationship.confidence
                    ),
                    physical_join_ready=(
                        join_mapping is not None
                    ),
                    join_mapping_id=(
                        join_mapping.id
                        if join_mapping
                        else None
                    ),
                    join_type=(
                        join_mapping.join_type
                        if join_mapping
                        else None
                    ),
                    source_metadata_table_id=(
                        join_mapping.source_metadata_table_id
                        if join_mapping
                        else None
                    ),
                    source_table_name=(
                        join_mapping.source_table.table_name
                        if join_mapping
                        else None
                    ),
                    source_metadata_column_id=(
                        join_mapping.source_metadata_column_id
                        if join_mapping
                        else None
                    ),
                    source_column_name=(
                        join_mapping.source_column.column_name
                        if join_mapping
                        else None
                    ),
                    target_metadata_table_id=(
                        join_mapping.target_metadata_table_id
                        if join_mapping
                        else None
                    ),
                    target_table_name=(
                        join_mapping.target_table.table_name
                        if join_mapping
                        else None
                    ),
                    target_metadata_column_id=(
                        join_mapping.target_metadata_column_id
                        if join_mapping
                        else None
                    ),
                    target_column_name=(
                        join_mapping.target_column.column_name
                        if join_mapping
                        else None
                    ),
                    warning=(
                        None
                        if join_mapping
                        else (
                            "No approved physical "
                            "join-column mapping exists."
                        )
                    ),
                )
            )

    return GovernedQueryPlanResponse(
        prompt=plan.prompt,
        normalized_prompt=(
            plan.normalized_prompt
        ),
        decision=plan.decision,
        is_allowed=plan.is_allowed,
        intent=plan.intent,
        overall_confidence=(
            plan.overall_confidence
        ),
        domain=domain_response,
        capabilities=(
            capability_responses
        ),
        entities=entity_responses,
        tables=table_responses,
        selected_columns=(
            selected_columns
        ),
        filters=filters,
        aggregation=(
            aggregation_response
        ),
        aggregations=(
            aggregation_responses
        ),
        group_by=group_by,
        order_by=order_by,
        semantic_joins=(
            semantic_joins
        ),
        approved_limit=(
            plan.approved_limit
        ),
        requires_clarification=(
            plan.decision
            == "requires_clarification"
        ),
        clarification_questions=(
            reasoning[
                "clarification_questions"
            ]
        ),
        governance_checks=[
            GovernanceCheckResponse(
                rule_code=(
                    check.rule_code
                ),
                passed=check.passed,
                severity=check.severity,
                message=check.message,
            )
            for check
            in plan.governance_checks
        ],
        warnings=list(
            dict.fromkeys(
                plan.warnings
            )
        ),
        blocked_reasons=list(
            dict.fromkeys(
                plan.blocked_reasons
            )
        ),
        explanation=(
            plan.explanation
        ),
    )
