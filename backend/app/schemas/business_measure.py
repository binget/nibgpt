from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
)


class BusinessMeasureCreate(BaseModel):
    business_entity_id: int
    metadata_column_id: int | None = None

    name: str
    aggregation_function: str
    
    temporal_behavior: str = "event"
    time_axis_column_id: int | None = None
    period_selection: str = "all_rows"
    historical_source_table_id: int | None = None
    historical_value_column_id: int | None = None

    trigger_phrases: str | None = None
    synonyms: str | None = None

    description: str | None = None

    confidence: int = 100

    approval_status: str = "draft"
    is_active: bool = True


class BusinessMeasureUpdate(BaseModel):
    business_entity_id: int | None = None
    metadata_column_id: int | None = None

    name: str | None = None
    aggregation_function: str | None = None
    
    temporal_behavior: str | None = None
    time_axis_column_id: int | None = None
    period_selection: str | None = None
    historical_source_table_id: int | None = None
    historical_value_column_id: int | None = None

    trigger_phrases: str | None = None
    synonyms: str | None = None

    description: str | None = None

    confidence: int | None = None

    approval_status: str | None = None
    is_active: bool | None = None


class BusinessMeasureEntityResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    name: str
    classification: str
    approval_status: str


class BusinessMeasureColumnResponse(BaseModel):
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


class BusinessMeasureResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    business_entity_id: int
    metadata_column_id: int | None

    name: str
    aggregation_function: str
    
    temporal_behavior: str
    time_axis_column_id: int | None
    period_selection: str
    historical_source_table_id: int | None
    historical_value_column_id: int | None

    trigger_phrases: str | None
    synonyms: str | None

    description: str | None

    confidence: int

    approval_status: str
    is_active: bool

    created_at: datetime
    updated_at: datetime

    entity: BusinessMeasureEntityResponse

    column: (
        BusinessMeasureColumnResponse
        | None
    )