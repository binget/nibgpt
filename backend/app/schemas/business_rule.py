from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BusinessRuleCreate(BaseModel):
    business_entity_id: int
    metadata_column_id: int

    name: str
    trigger_phrase: str

    synonyms: str | None = None

    operator: str = "="
    rule_value: str

    description: str | None = None

    confidence: int = 100

    approval_status: str = "draft"
    is_active: bool = True


class BusinessRuleUpdate(BaseModel):
    business_entity_id: int | None = None
    metadata_column_id: int | None = None

    name: str | None = None
    trigger_phrase: str | None = None

    synonyms: str | None = None

    operator: str | None = None
    rule_value: str | None = None

    description: str | None = None

    confidence: int | None = None

    approval_status: str | None = None
    is_active: bool | None = None


class BusinessRuleEntityResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    name: str
    classification: str
    approval_status: str


class BusinessRuleColumnResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    metadata_table_id: int
    column_name: str
    business_name: str | None
    data_type: str
    classification: str
    is_sensitive: bool


class BusinessRuleResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    business_entity_id: int
    metadata_column_id: int

    name: str
    trigger_phrase: str

    synonyms: str | None

    operator: str
    rule_value: str

    description: str | None

    confidence: int

    approval_status: str
    is_active: bool

    created_at: datetime
    updated_at: datetime

    entity: BusinessRuleEntityResponse
    column: BusinessRuleColumnResponse