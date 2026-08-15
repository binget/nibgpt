from typing import Literal

from pydantic import BaseModel, Field


QueryIntent = Literal[
    "select",
    "count",
    "aggregation",
    "ranking",
    "trend",
    "comparison",
    "expiry_monitoring",
]


FilterOperator = Literal[
    "=",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "contains",
    "this_day",
    "this_week",
    "this_month",
    "this_year",
    "last_day",
    "last_week",
    "last_month",
    "last_year",
    "next_day",
    "next_week",
    "next_month",
    "next_year",
]


AggregationFunction = Literal[
    "count",
    "sum",
    "average",
    "minimum",
    "maximum",
]


SortDirection = Literal[
    "asc",
    "desc",
]


class QueryPlanRequest(BaseModel):
    prompt: str = Field(
        min_length=2,
        max_length=2000,
    )

    data_source_id: int | None = None

    maximum_plans: int = Field(
        default=3,
        ge=1,
        le=5,
    )

    default_limit: int = Field(
        default=100,
        ge=1,
        le=1000,
    )


class PlannedColumnResponse(BaseModel):
    id: int
    column_name: str
    business_name: str | None
    data_type: str
    purpose: str
    confidence: int


class PlannedFilterResponse(BaseModel):
    column_id: int
    column_name: str
    business_name: str | None
    operator: FilterOperator
    value: str | int | float | bool | None
    confidence: int
    reason: str


class PlannedAggregationResponse(BaseModel):
    function: AggregationFunction
    column_id: int | None
    column_name: str | None
    alias: str
    confidence: int


class PlannedSortResponse(BaseModel):
    column_id: int
    column_name: str
    direction: SortDirection
    confidence: int


class CandidateQueryPlanResponse(BaseModel):
    position: int

    metadata_table_id: int
    data_source_id: int

    schema_name: str | None
    table_name: str
    business_name: str | None

    intent: QueryIntent

    selected_columns: list[PlannedColumnResponse]
    filters: list[PlannedFilterResponse]
    aggregation: PlannedAggregationResponse | None
    group_by: list[PlannedColumnResponse]
    order_by: list[PlannedSortResponse]

    row_limit: int

    confidence: int
    requires_clarification: bool

    warnings: list[str]
    reasons: list[str]


class QueryPlanResponse(BaseModel):
    prompt: str
    normalized_prompt: str

    is_safe: bool
    blocked_reason: str | None

    intent: str
    overall_confidence: int

    recommended_plan_position: int | None
    requires_user_selection: bool

    candidate_plans: list[CandidateQueryPlanResponse]

    warnings: list[str]
