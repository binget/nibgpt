from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.query_planner import (
    create_query_plans,
)
from app.database.session import get_db
from app.schemas.query_plan import (
    CandidateQueryPlanResponse,
    PlannedAggregationResponse,
    PlannedColumnResponse,
    PlannedFilterResponse,
    PlannedSortResponse,
    QueryPlanRequest,
    QueryPlanResponse,
)


router = APIRouter(
    prefix="/api/query-plan",
    tags=["Safe Query Planner"],
)

def convert_candidate_plan(
    plan,
) -> CandidateQueryPlanResponse:
    selected_columns = [
        PlannedColumnResponse(
            id=item.column.id,
            column_name=item.column.column_name,
            business_name=item.column.business_name,
            data_type=item.column.data_type,
            purpose=item.purpose,
            confidence=item.confidence,
        )
        for item in plan.selected_columns
    ]

    filters = [
        PlannedFilterResponse(
            column_id=item.column.id,
            column_name=item.column.column_name,
            business_name=item.column.business_name,
            operator=item.operator,
            value=item.value,
            confidence=item.confidence,
            reason=item.reason,
        )
        for item in plan.filters
    ]

    aggregation = None

    if plan.aggregation:
        aggregation = PlannedAggregationResponse(
            function=plan.aggregation.function,
            column_id=(
                plan.aggregation.column.id
                if plan.aggregation.column
                else None
            ),
            column_name=(
                plan.aggregation.column.column_name
                if plan.aggregation.column
                else None
            ),
            alias=plan.aggregation.alias,
            confidence=(
                plan.aggregation.confidence
            ),
        )

    group_by = [
        PlannedColumnResponse(
            id=item.column.id,
            column_name=item.column.column_name,
            business_name=item.column.business_name,
            data_type=item.column.data_type,
            purpose=item.purpose,
            confidence=item.confidence,
        )
        for item in plan.group_by
    ]

    order_by = [
        PlannedSortResponse(
            column_id=item.column.id,
            column_name=item.column.column_name,
            direction=item.direction,
            confidence=item.confidence,
        )
        for item in plan.order_by
    ]

    table = plan.table_match.table

    return CandidateQueryPlanResponse(
        position=plan.position,
        metadata_table_id=table.id,
        data_source_id=table.data_source_id,
        schema_name=table.schema_name,
        table_name=table.table_name,
        business_name=table.business_name,
        intent=plan.intent,
        selected_columns=selected_columns,
        filters=filters,
        aggregation=aggregation,
        group_by=group_by,
        order_by=order_by,
        row_limit=plan.row_limit,
        confidence=plan.confidence,
        requires_clarification=(
            plan.requires_clarification
        ),
        warnings=plan.warnings,
        reasons=plan.reasons,
    )


@router.post(
    "/generate",
    response_model=QueryPlanResponse,
)
def generate_query_plan(
    payload: QueryPlanRequest,
    database: Session = Depends(get_db),
):
    result = create_query_plans(
        database=database,
        prompt=payload.prompt.strip(),
        data_source_id=payload.data_source_id,
        maximum_plans=payload.maximum_plans,
        default_limit=payload.default_limit,
    )

    plan_responses = [
    convert_candidate_plan(plan)
    for plan in result["candidate_plans"]
]

    for plan in result["candidate_plans"]:
        selected_columns = [
            PlannedColumnResponse(
                id=item.column.id,
                column_name=(
                    item.column.column_name
                ),
                business_name=(
                    item.column.business_name
                ),
                data_type=(
                    item.column.data_type
                ),
                purpose=item.purpose,
                confidence=item.confidence,
            )
            for item in plan.selected_columns
        ]

        filters = [
            PlannedFilterResponse(
                column_id=item.column.id,
                column_name=(
                    item.column.column_name
                ),
                business_name=(
                    item.column.business_name
                ),
                operator=item.operator,
                value=item.value,
                confidence=item.confidence,
                reason=item.reason,
            )
            for item in plan.filters
        ]

        aggregation = None

        if plan.aggregation:
            aggregation = (
                PlannedAggregationResponse(
                    function=(
                        plan.aggregation.function
                    ),
                    column_id=(
                        plan.aggregation.column.id
                        if plan.aggregation.column
                        else None
                    ),
                    column_name=(
                        plan.aggregation
                        .column.column_name
                        if plan.aggregation.column
                        else None
                    ),
                    alias=(
                        plan.aggregation.alias
                    ),
                    confidence=(
                        plan.aggregation.confidence
                    ),
                )
            )

        group_by = [
            PlannedColumnResponse(
                id=item.column.id,
                column_name=(
                    item.column.column_name
                ),
                business_name=(
                    item.column.business_name
                ),
                data_type=(
                    item.column.data_type
                ),
                purpose=item.purpose,
                confidence=item.confidence,
            )
            for item in plan.group_by
        ]

        order_by = [
            PlannedSortResponse(
                column_id=item.column.id,
                column_name=(
                    item.column.column_name
                ),
                direction=item.direction,
                confidence=item.confidence,
            )
            for item in plan.order_by
        ]

        table = plan.table_match.table

        plan_responses.append(
            CandidateQueryPlanResponse(
                position=plan.position,
                metadata_table_id=table.id,
                data_source_id=(
                    table.data_source_id
                ),
                schema_name=(
                    table.schema_name
                ),
                table_name=table.table_name,
                business_name=(
                    table.business_name
                ),
                intent=plan.intent,
                selected_columns=(
                    selected_columns
                ),
                filters=filters,
                aggregation=aggregation,
                group_by=group_by,
                order_by=order_by,
                row_limit=plan.row_limit,
                confidence=plan.confidence,
                requires_clarification=(
                    plan.requires_clarification
                ),
                warnings=plan.warnings,
                reasons=plan.reasons,
            )
        )

    warnings = list(
        result["warnings"]
    )

    if result[
        "requires_user_selection"
    ]:
        warnings.append(
            "Multiple or low-confidence plans require user confirmation."
        )

    return QueryPlanResponse(
        prompt=result["prompt"],
        normalized_prompt=result[
            "normalized_prompt"
        ],
        is_safe=result["is_safe"],
        blocked_reason=result[
            "blocked_reason"
        ],
        intent=result["intent"],
        overall_confidence=result[
            "overall_confidence"
        ],
        recommended_plan_position=result[
            "recommended_plan_position"
        ],
        requires_user_selection=result[
            "requires_user_selection"
        ],
        candidate_plans=plan_responses,
        warnings=warnings,
    )
