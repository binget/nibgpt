from pydantic import (
    BaseModel,
    Field,
)

class ReportingContext(BaseModel):
    measure: str | None = None
    dimension: str | None = None
    status: str | None = None

    ranking: str | None = None
    limit: int | None = None

    sort_direction: str | None = None

    district: str | None = None
    branch: str | None = None
    currency: str | None = None
    customer: str | None = None
    category: str | None = None

    date_from: str | None = None
    date_to: str | None = None
    period: str | None = None

    filters: dict[str, str] = Field(
        default_factory=dict
    )

    previous_prompt: str | None = None

class OrchestratorRequest(BaseModel):
    prompt: str = Field(
        min_length=1,
        max_length=5000,
    )

    conversation_id: int | None = None
    
    previous_prompt: str | None = None

    context: ReportingContext | None = None
    
    

    requested_limit: int = 100
    maximum_entities: int = 6
    maximum_path_depth: int = 4
    
    user_role: str = "analyst"


class OrchestratorResponse(BaseModel):
    route: str
    confidence: int
    reason: str

    success: bool

    answer: str | None = None
    report: dict | None = None
    context: ReportingContext | None = None
    
    decision: str | None = None

    errors: list[str] = Field(
        default_factory=list
    )

    explanation: list[str] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )

    sources: list[dict] = Field(
        default_factory=list
    )

    retrieved_at: str | None = None