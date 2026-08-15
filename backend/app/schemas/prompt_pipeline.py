from typing import Literal

from pydantic import BaseModel, Field


PromptIntent = Literal[
    "select",
    "count",
    "aggregation",
    "ranking",
    "trend",
    "comparison",
    "expiry_monitoring",
    "blocked",
    "unknown",
]


class PromptPipelineRequest(BaseModel):
    prompt: str = Field(
        min_length=2,
        max_length=2000,
    )

    data_source_id: int | None = None

    maximum_results: int = Field(
        default=5,
        ge=1,
        le=20,
    )


class ExtractedEntityResponse(BaseModel):
    value: str
    entity_type: str
    confidence: int


class ResolvedColumnResponse(BaseModel):
    id: int
    column_name: str
    business_name: str | None
    description: str | None
    data_type: str
    classification: str
    is_sensitive: bool
    ai_access_allowed: bool

    score: int
    confidence: int
    matched_terms: list[str]
    reasons: list[str]


class ResolvedTableResponse(BaseModel):
    id: int
    data_source_id: int
    schema_name: str | None
    table_name: str
    business_name: str | None
    description: str | None
    department: str | None
    data_owner: str | None
    classification: str
    definition_status: str
    ai_access_allowed: bool

    score: int
    confidence: int
    matched_terms: list[str]
    reasons: list[str]

    columns: list[ResolvedColumnResponse]


class PromptPipelineResponse(BaseModel):
    prompt: str
    normalized_prompt: str

    intent: PromptIntent
    intent_confidence: int

    entities: list[ExtractedEntityResponse]
    keywords: list[str]
    time_expressions: list[str]
    status_terms: list[str]
    aggregation_terms: list[str]

    is_safe: bool
    blocked_reason: str | None

    metadata_confidence: int
    overall_confidence: int

    matched_tables: list[ResolvedTableResponse]

    warnings: list[str]
    explanation: list[str]