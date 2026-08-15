from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.governance_engine import (
    evaluate_governance,
)
from app.api.query_plan import (
    convert_candidate_plan,
)
from app.database.session import get_db
from app.schemas.governance import (
    GovernanceEvaluationRequest,
    GovernanceEvaluationResponse,
    GovernanceRuleResult,
)


router = APIRouter(
    prefix="/api/governance",
    tags=["AI Governance"],
)


@router.post(
    "/evaluate",
    response_model=GovernanceEvaluationResponse,
)
def evaluate_query_governance(
    payload: GovernanceEvaluationRequest,
    database: Session = Depends(get_db),
):
    result = evaluate_governance(
        database=database,
        prompt=payload.prompt.strip(),
        data_source_id=payload.data_source_id,
        user_role=payload.user_role,
        requested_plan_position=(
            payload.requested_plan_position
        ),
        maximum_plans=payload.maximum_plans,
        requested_limit=payload.requested_limit,
    )

    selected_plan_response = None

    if result.selected_plan is not None:
        selected_plan_response = (
            convert_candidate_plan(
                result.selected_plan
            )
        )

    return GovernanceEvaluationResponse(
        prompt=payload.prompt.strip(),
        decision=result.decision,
        is_allowed=result.is_allowed,
        selected_plan_position=(
            result.selected_plan_position
        ),
        selected_plan=(
            selected_plan_response
        ),
        original_row_limit=(
            result.original_row_limit
        ),
        approved_row_limit=(
            result.approved_row_limit
        ),
        requires_human_review=(
            result.requires_human_review
        ),
        requires_user_selection=(
            result.requires_user_selection
        ),
        rule_results=[
            GovernanceRuleResult(
                rule_code=rule.rule_code,
                rule_name=rule.rule_name,
                passed=rule.passed,
                severity=rule.severity,
                message=rule.message,
            )
            for rule in result.rule_results
        ],
        warnings=result.warnings,
        blocked_reasons=(
            result.blocked_reasons
        ),
    )
