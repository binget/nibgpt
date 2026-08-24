from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
)


class BusinessDimensionCreate(BaseModel):
    business_entity_id: int
    metadata_column_id: int

    name: str

    trigger_phrases: str | None = None
    synonyms: str | None = None

    description: str | None = None

    confidence: int = 100

    approval_status: str = "draft"
    is_active: bool = True


class BusinessDimensionUpdate(BaseModel):
    business_entity_id: int | None = None
    metadata_column_id: int | None = None

    name: str | None = None

    trigger_phrases: str | None = None
    synonyms: str | None = None

    description: str | None = None

    confidence: int | None = None

    approval_status: str | None = None
    is_active: bool | None = None


class BusinessDimensionEntityResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    name: str
    classification: str
    approval_status: str


class BusinessDimensionColumnResponse(BaseModel):
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


class BusinessDimensionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    business_entity_id: int
    metadata_column_id: int

    name: str

    trigger_phrases: str | None
    synonyms: str | None

    description: str | None

    confidence: int

    approval_status: str
    is_active: bool

    created_at: datetime
    updated_at: datetime

    entity: BusinessDimensionEntityResponse
    column: BusinessDimensionColumnResponse