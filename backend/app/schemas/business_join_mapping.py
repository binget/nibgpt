from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


JoinType = Literal[
    "inner",
    "left",
    "right",
    "full",
]


ApprovalStatus = Literal[
    "draft",
    "generated",
    "approved",
    "rejected",
]


class BusinessJoinMappingCreate(BaseModel):
    relationship_id: int

    source_metadata_table_id: int
    source_metadata_column_id: int

    target_metadata_table_id: int
    target_metadata_column_id: int

    join_type: JoinType = "inner"

    description: str | None = None

    confidence: int = Field(
        default=100,
        ge=0,
        le=100,
    )


class BusinessJoinMappingUpdate(BaseModel):
    join_type: JoinType | None = None

    description: str | None = None

    confidence: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    approval_status: ApprovalStatus | None = None

    is_active: bool | None = None


class JoinTableSummary(BaseModel):
    id: int
    data_source_id: int
    schema_name: str | None
    table_name: str
    business_name: str | None

    model_config = ConfigDict(
        from_attributes=True
    )


class JoinColumnSummary(BaseModel):
    id: int
    metadata_table_id: int
    column_name: str
    business_name: str | None
    data_type: str
    classification: str
    is_sensitive: bool

    model_config = ConfigDict(
        from_attributes=True
    )


class BusinessJoinMappingResponse(BaseModel):
    id: int
    relationship_id: int

    source_metadata_table_id: int
    source_metadata_column_id: int

    target_metadata_table_id: int
    target_metadata_column_id: int

    join_type: str
    description: str | None

    confidence: int
    approval_status: str
    is_active: bool

    created_at: datetime
    updated_at: datetime

    source_table: JoinTableSummary
    source_column: JoinColumnSummary

    target_table: JoinTableSummary
    target_column: JoinColumnSummary

    model_config = ConfigDict(
        from_attributes=True
    )


class BusinessJoinMappingSuggestionResponse(BaseModel):
    relationship_id: int

    source_metadata_table_id: int
    source_metadata_column_id: int

    target_metadata_table_id: int
    target_metadata_column_id: int

    join_type: str
    confidence: int

    description: str
    reasons: list[str]
