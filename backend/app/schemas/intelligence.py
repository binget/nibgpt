from pydantic import BaseModel, Field


class PromptAnalysisRequest(BaseModel):
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


class ColumnMatchResponse(BaseModel):
    id: int
    column_name: str
    business_name: str | None
    description: str | None
    data_type: str
    classification: str
    is_sensitive: bool
    ai_access_allowed: bool
    score: int
    matched_terms: list[str]


class TableMatchResponse(BaseModel):
    id: int
    data_source_id: int
    schema_name: str | None
    table_name: str
    business_name: str | None
    description: str | None
    department: str | None
    data_owner: str | None
    classification: str
    ai_access_allowed: bool
    score: int
    confidence: int
    matched_terms: list[str]
    reasons: list[str]
    columns: list[ColumnMatchResponse]
    suggested_questions: list[str]


class PromptAnalysisResponse(BaseModel):
    prompt: str
    normalized_prompt: str
    intent: str
    confidence: int
    result_count: int
    warnings: list[str]
    matches: list[TableMatchResponse]
