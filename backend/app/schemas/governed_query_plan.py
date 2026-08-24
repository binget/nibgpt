from typing import Literal

from pydantic import BaseModel, Field


PlanDecision = Literal[
    "approved",
    "requires_clarification",
    "blocked",
]


AggregationFunction = Literal[
    "count",
    "sum",
    "average",
    "minimum",
    "maximum",
]


FilterOperator = Literal[
    "=",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "contains",
    "in",
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
    "is_null",
    "is_not_null",
]


SortDirection = Literal[
    "asc",
    "desc",
]


class GovernedQueryPlanRequest(BaseModel):
    prompt: str = Field(
        min_length=2,
        max_length=2000,
    )

    domain_id: int | None = None

    requested_limit: int = Field(
        default=100,
        ge=1,
        le=1000,
    )

    maximum_entities: int = Field(
        default=6,
        ge=1,
        le=15,
    )

    maximum_path_depth: int = Field(
        default=4,
        ge=1,
        le=8,
    )

    # Temporary until authentication and RBAC are connected.
    user_role: str = Field(
        default="standard_user",
        min_length=2,
        max_length=100,
    )


class GovernedPlanDomainResponse(BaseModel):
    id: int
    name: str
    confidence: int


class GovernedPlanCapabilityResponse(BaseModel):
    id: int
    name: str
    confidence: int


class GovernedPlanEntityResponse(BaseModel):
    id: int
    name: str
    classification: str
    confidence: int


class GovernedPlanTableResponse(BaseModel):
    metadata_table_id: int
    data_source_id: int

    schema_name: str | None
    table_name: str
    business_name: str | None

    entity_id: int
    entity_name: str

    mapping_type: str
    mapping_confidence: int


class GovernedPlanColumnResponse(BaseModel):
    metadata_column_id: int
    metadata_table_id: int

    column_name: str
    business_name: str | None
    data_type: str

    classification: str
    is_sensitive: bool

    purpose: str
    confidence: int


class GovernedPlanFilterResponse(BaseModel):
    metadata_column_id: int
    metadata_table_id: int

    column_name: str
    business_name: str | None

    operator: FilterOperator

    value: (
        str
        | int
        | float
        | bool
        | list[str]
        | list[int]
        | None
    )

    confidence: int
    reason: str


class GovernedPlanAggregationResponse(BaseModel):
    function: AggregationFunction

    metadata_column_id: int | None
    metadata_table_id: int | None

    column_name: str | None
    alias: str

    confidence: int


class GovernedPlanGroupingResponse(BaseModel):
    metadata_column_id: int
    metadata_table_id: int

    column_name: str
    business_name: str | None

    confidence: int


class GovernedPlanSortResponse(BaseModel):
    metadata_column_id: int
    metadata_table_id: int

    column_name: str
    direction: SortDirection

    confidence: int


class GovernedSemanticJoinResponse(BaseModel):
    relationship_id: int

    source_entity_id: int
    source_entity_name: str

    relationship_name: str

    target_entity_id: int
    target_entity_name: str

    confidence: int

    physical_join_ready: bool

    join_mapping_id: int | None
    join_type: str | None

    source_metadata_table_id: int | None
    source_table_name: str | None

    source_metadata_column_id: int | None
    source_column_name: str | None

    target_metadata_table_id: int | None
    target_table_name: str | None

    target_metadata_column_id: int | None
    target_column_name: str | None

    warning: str | None


class GovernanceCheckResponse(BaseModel):
    rule_code: str
    passed: bool
    severity: Literal[
        "info",
        "warning",
        "critical",
    ]
    message: str


class GovernedQueryPlanResponse(BaseModel):
    prompt: str
    normalized_prompt: str

    decision: PlanDecision
    is_allowed: bool

    intent: str
    overall_confidence: int

    domain: GovernedPlanDomainResponse | None

    capabilities: list[
        GovernedPlanCapabilityResponse
    ]

    entities: list[
        GovernedPlanEntityResponse
    ]

    tables: list[
        GovernedPlanTableResponse
    ]

    selected_columns: list[
        GovernedPlanColumnResponse
    ]

    filters: list[
        GovernedPlanFilterResponse
    ]

    aggregation: (
        GovernedPlanAggregationResponse
        | None
    )

    aggregations: list[
        GovernedPlanAggregationResponse
    ]

    group_by: list[
        GovernedPlanGroupingResponse
    ]

    group_by: list[
        GovernedPlanGroupingResponse
    ]

    order_by: list[
        GovernedPlanSortResponse
    ]

    semantic_joins: list[
        GovernedSemanticJoinResponse
    ]

    approved_limit: int

    requires_clarification: bool
    clarification_questions: list[str]

    governance_checks: list[
        GovernanceCheckResponse
    ]

    warnings: list[str]
    blocked_reasons: list[str]
    explanation: list[str]
