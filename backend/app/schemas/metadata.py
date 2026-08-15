from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Classification = Literal[
    "public",
    "internal",
    "confidential",
    "restricted",
]


class MetadataColumnResponse(BaseModel):
    id: int
    column_name: str
    data_type: str
    ordinal_position: int
    is_nullable: bool
    is_primary_key: bool
    default_value: str | None
    business_name: str | None
    description: str | None
    classification: str
    ai_access_allowed: bool
    is_sensitive: bool
    is_enabled: bool
    synonyms: str | None
    definition_status: str
    is_discovered: bool
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetadataTableSummaryResponse(BaseModel):
    id: int
    data_source_id: int
    schema_name: str | None
    table_name: str
    object_type: str
    business_name: str | None
    description: str | None
    data_owner: str | None
    department: str | None
    classification: str
    ai_access_allowed: bool
    is_enabled: bool
    discovered_at: datetime
    synonyms: str | None
    suggested_questions: str | None
    definition_status: str
    is_discovered: bool
    last_seen_at: datetime
    business_purpose: str | None
    business_terms: str | None
    common_filters: str | None
    common_measures: str | None
    primary_business_keys: str | None
    related_entities: str | None
    ai_notes: str | None
    knowledge_status: str

    model_config = ConfigDict(from_attributes=True)


class MetadataTableDetailResponse(
    MetadataTableSummaryResponse
):
    columns: list[MetadataColumnResponse]


class MetadataScanResponse(BaseModel):
    success: bool
    data_source_id: int

    schemas_scanned: int
    tables_discovered: int
    views_discovered: int
    columns_discovered: int

    new_tables: int
    updated_tables: int
    removed_tables: int

    new_columns: int
    updated_columns: int
    removed_columns: int

    message: str


class MetadataTableUpdate(BaseModel):
    business_name: str | None = Field(
        default=None,
        max_length=250,
    )
    description: str | None = None
    data_owner: str | None = Field(
        default=None,
        max_length=150,
    )
    department: str | None = Field(
        default=None,
        max_length=150,
    )
    classification: Classification | None = None
    ai_access_allowed: bool | None = None
    is_enabled: bool | None = None
    synonyms: str | None = None
    suggested_questions: str | None = None
    definition_status: str | None = None
    business_purpose: str | None = None
    business_terms: str | None = None
    common_filters: str | None = None
    common_measures: str | None = None
    primary_business_keys: str | None = None
    related_entities: str | None = None
    ai_notes: str | None = None
    knowledge_status: str | None = None


class MetadataColumnUpdate(BaseModel):
    business_name: str | None = Field(
        default=None,
        max_length=250,
    )
    description: str | None = None
    classification: Classification | None = None
    ai_access_allowed: bool | None = None
    is_sensitive: bool | None = None
    is_enabled: bool | None = None
    synonyms: str | None = None
    definition_status: str | None = None


class GeneratedColumnDefinition(BaseModel):
    column_id: int
    technical_name: str
    business_name: str
    description: str
    synonyms: list[str]
    classification: str
    is_sensitive: bool


class GeneratedTableDefinition(BaseModel):
    table_id: int
    technical_name: str
    business_name: str
    description: str
    synonyms: list[str]
    suggested_questions: list[str]
    columns: list[GeneratedColumnDefinition]


class DefinitionApprovalRequest(BaseModel):
    approved: bool

class GeneratedKnowledgeProfile(BaseModel):
    table_id: int
    technical_name: str
    business_name: str
    business_purpose: str

    business_terms: list[str]
    common_questions: list[str]
    common_filters: list[str]
    common_measures: list[str]
    primary_business_keys: list[str]
    related_entities: list[str]

    ai_notes: str
    confidence: int
    reasons: list[str]


class KnowledgeApprovalRequest(BaseModel):
    approved: bool