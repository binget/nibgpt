from pydantic import BaseModel


class DomainReadinessResponse(BaseModel):
    data_source_id: int
    domain_name: str
    database_type: str

    readiness_score: int
    maturity_level: str
    status: str

    approved_knowledge_percentage: int
    approved_dictionary_percentage: int
    governance_percentage: int

    requires_attention: bool
    attention_reason: str | None


class ExecutiveHighlightResponse(BaseModel):
    severity: str
    title: str
    message: str


class ExecutiveDashboardResponse(BaseModel):
    enterprise_readiness: int
    readiness_label: str

    connected_business_systems: int
    ai_ready_business_systems: int
    systems_requiring_attention: int

    governance_compliance: int
    knowledge_maturity: int

    domains: list[DomainReadinessResponse]
    highlights: list[ExecutiveHighlightResponse]
