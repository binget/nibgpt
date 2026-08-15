from pydantic import BaseModel, Field


class ReasoningRequest(BaseModel):
    prompt: str = Field(
        min_length=2,
        max_length=2000,
    )

    domain_id: int | None = None

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


class ReasoningDomainResponse(BaseModel):
    id: int
    name: str
    description: str | None
    confidence: int
    reasons: list[str]


class ReasoningCapabilityResponse(BaseModel):
    id: int
    domain_id: int
    name: str
    description: str | None
    capability_type: str
    maturity_level: str
    confidence: int
    reasons: list[str]


class ReasoningEntityResponse(BaseModel):
    id: int
    domain_id: int
    name: str
    description: str | None
    classification: str
    confidence: int
    matched_terms: list[str]
    reasons: list[str]


class ReasoningRelationshipStepResponse(BaseModel):
    relationship_id: int

    source_entity_id: int
    source_entity_name: str

    relationship_name: str

    target_entity_id: int
    target_entity_name: str

    confidence: int


class ReasoningPathResponse(BaseModel):
    start_entity_id: int
    end_entity_id: int

    steps: list[
        ReasoningRelationshipStepResponse
    ]

    confidence: int
    explanation: str


class ReasoningColumnResponse(BaseModel):
    id: int
    column_name: str
    business_name: str | None
    description: str | None
    data_type: str
    classification: str
    is_sensitive: bool
    confidence: int
    matched_terms: list[str]


class ReasoningTableResponse(BaseModel):
    id: int
    data_source_id: int

    schema_name: str | None
    table_name: str
    business_name: str | None
    description: str | None

    entity_id: int
    entity_name: str
    mapping_type: str
    mapping_confidence: int

    columns: list[
        ReasoningColumnResponse
    ]


class ReasoningPlanResponse(BaseModel):
    prompt: str
    normalized_prompt: str

    intent: str
    intent_confidence: int

    selected_domain: (
        ReasoningDomainResponse | None
    )

    matched_capabilities: list[
        ReasoningCapabilityResponse
    ]

    matched_entities: list[
        ReasoningEntityResponse
    ]

    relationship_paths: list[
        ReasoningPathResponse
    ]

    physical_tables: list[
        ReasoningTableResponse
    ]

    overall_confidence: int

    requires_clarification: bool
    clarification_questions: list[str]

    warnings: list[str]
    explanation: list[str]
