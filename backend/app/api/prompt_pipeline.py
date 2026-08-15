from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.prompt_pipeline import (
    analyze_prompt_pipeline,
)
from app.database.session import get_db
from app.schemas.prompt_pipeline import (
    ExtractedEntityResponse,
    PromptPipelineRequest,
    PromptPipelineResponse,
    ResolvedColumnResponse,
    ResolvedTableResponse,
)


router = APIRouter(
    prefix="/api/prompt-pipeline",
    tags=["Prompt Pipeline"],
)


@router.post(
    "/analyze",
    response_model=PromptPipelineResponse,
)
def analyze_prompt(
    payload: PromptPipelineRequest,
    database: Session = Depends(get_db),
):
    result = analyze_prompt_pipeline(
        database=database,
        prompt=payload.prompt.strip(),
        data_source_id=payload.data_source_id,
        maximum_results=payload.maximum_results,
    )

    table_responses: list[
        ResolvedTableResponse
    ] = []

    for match in result["matched_tables"]:
        column_responses = [
            ResolvedColumnResponse(
                id=column_match.column.id,
                column_name=(
                    column_match.column.column_name
                ),
                business_name=(
                    column_match.column.business_name
                ),
                description=(
                    column_match.column.description
                ),
                data_type=(
                    column_match.column.data_type
                ),
                classification=(
                    column_match.column.classification
                ),
                is_sensitive=(
                    column_match.column.is_sensitive
                ),
                ai_access_allowed=(
                    column_match.column.ai_access_allowed
                ),
                score=column_match.score,
                confidence=(
                    column_match.confidence
                ),
                matched_terms=(
                    column_match.matched_terms
                ),
                reasons=column_match.reasons,
            )
            for column_match in match.columns
        ]

        table_responses.append(
            ResolvedTableResponse(
                id=match.table.id,
                data_source_id=(
                    match.table.data_source_id
                ),
                schema_name=(
                    match.table.schema_name
                ),
                table_name=(
                    match.table.table_name
                ),
                business_name=(
                    match.table.business_name
                ),
                description=(
                    match.table.description
                ),
                department=(
                    match.table.department
                ),
                data_owner=(
                    match.table.data_owner
                ),
                classification=(
                    match.table.classification
                ),
                definition_status=(
                    match.table.definition_status
                ),
                ai_access_allowed=(
                    match.table.ai_access_allowed
                ),
                score=match.score,
                confidence=match.confidence,
                matched_terms=(
                    match.matched_terms
                ),
                reasons=match.reasons,
                columns=column_responses,
            )
        )

    return PromptPipelineResponse(
        prompt=result["prompt"],
        normalized_prompt=result[
            "normalized_prompt"
        ],
        intent=result["intent"],
        intent_confidence=result[
            "intent_confidence"
        ],
        entities=[
            ExtractedEntityResponse(
                value=entity.value,
                entity_type=entity.entity_type,
                confidence=entity.confidence,
            )
            for entity in result["entities"]
        ],
        keywords=result["keywords"],
        time_expressions=result[
            "time_expressions"
        ],
        status_terms=result[
            "status_terms"
        ],
        aggregation_terms=result[
            "aggregation_terms"
        ],
        is_safe=result["is_safe"],
        blocked_reason=result[
            "blocked_reason"
        ],
        metadata_confidence=result[
            "metadata_confidence"
        ],
        overall_confidence=result[
            "overall_confidence"
        ],
        matched_tables=table_responses,
        warnings=result["warnings"],
        explanation=result["explanation"],
    )