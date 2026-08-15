from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.query_plan import CandidateQueryPlanResponse


UserRole = Literal[
    "administrator",
    "data_steward",
    "manager",
    "analyst",
    "standard_user",
]


DecisionStatus = Literal[
    "approved",
    "requires_review",
    "blocked",
]


class GovernanceEvaluationRequest(BaseModel):
    prompt: str = Field(
        min_length=2,
        max_length=2000,
    )

    data_source_id: int | None = None

    user_role: UserRole = "standard_user"

    requested_plan_position: int | None = Field(
        default=None,
        ge=1,
        le=5,
    )

    maximum_plans: int = Field(
        default=3,
        ge=1,
        le=5,
    )

    requested_limit: int = Field(
        default=100,
        ge=1,
        le=1000,
    )


class GovernanceRuleResult(BaseModel):
    rule_code: str
    rule_name: str
    passed: bool
    severity: Literal[
        "info",
        "warning",
        "critical",
    ]
    message: str


class GovernanceEvaluationResponse(BaseModel):
    prompt: str

    decision: DecisionStatus
    is_allowed: bool

    selected_plan_position: int | None
    selected_plan: CandidateQueryPlanResponse | None

    original_row_limit: int | None
    approved_row_limit: int | None

    requires_human_review: bool
    requires_user_selection: bool

    rule_results: list[GovernanceRuleResult]
    warnings: list[str]
    blocked_reasons: list[str]
