from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.prompt_intelligence import (
    analyze_prompt,
    calculate_confidence,
    create_suggested_questions,
)
from app.database.session import get_db
from app.schemas.intelligence import (
    ColumnMatchResponse,
    PromptAnalysisRequest,
    PromptAnalysisResponse,
    TableMatchResponse,
)


router = APIRouter(
    prefix="/api/intelligence",
    tags=["Prompt Intelligence"],
)


@router.post(
    "/analyze",
    response_model=PromptAnalysisResponse,
)
def analyze_user_prompt(
    payload: PromptAnalysisRequest,
    database: Session = Depends(get_db),
):
    result = analyze_prompt(
        database=database,
        prompt=payload.prompt.strip(),
        data_source_id=payload.data_source_id,
        maximum_results=payload.maximum_results,
    )

    response_matches: list[
        TableMatchResponse
    ] = []

    for match in result["matches"]:
        column_responses = [
            ColumnMatchResponse(
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
                matched_terms=(
                    column_match.matched_terms
                ),
            )
            for column_match in match.columns
        ]

        response_matches.append(
            TableMatchResponse(
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
                ai_access_allowed=(
                    match.table.ai_access_allowed
                ),
                score=match.score,
                confidence=calculate_confidence(
                    match
                ),
                matched_terms=(
                    match.matched_terms
                ),
                reasons=match.reasons,
                columns=column_responses,
                suggested_questions=(
                    create_suggested_questions(
                        match.table,
                        match.columns,
                    )
                ),
            )
        )

    return PromptAnalysisResponse(
        prompt=result["prompt"],
        normalized_prompt=(
            result["normalized_prompt"]
        ),
        intent=result["intent"],
        confidence=result["confidence"],
        result_count=len(response_matches),
        warnings=result["warnings"],
        matches=response_matches,
    )
