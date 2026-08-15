from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Classification = Literal[
    "public",
    "internal",
    "confidential",
    "restricted",
]

ApprovalStatus = Literal[
    "draft",
    "generated",
    "approved",
    "rejected",
]

MappingType = Literal[
    "primary",
    "supporting",
    "reference",
]


class BusinessDomainCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=200,
    )
    description: str | None = None
    department: str | None = Field(
        default=None,
        max_length=150,
    )
    owner: str | None = Field(
        default=None,
        max_length=150,
    )


class BusinessDomainUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )
    description: str | None = None
    department: str | None = Field(
        default=None,
        max_length=150,
    )
    owner: str | None = Field(
        default=None,
        max_length=150,
    )
    is_active: bool | None = None


class BusinessDomainResponse(BaseModel):
    id: int
    name: str
    description: str | None
    department: str | None
    owner: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EntityTableMappingCreate(BaseModel):
    metadata_table_id: int
    mapping_type: MappingType = "primary"
    confidence: int = Field(
        default=100,
        ge=0,
        le=100,
    )


class EntityTableMappingResponse(BaseModel):
    id: int
    metadata_table_id: int
    mapping_type: str
    confidence: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BusinessEntityCreate(BaseModel):
    domain_id: int
    name: str = Field(
        min_length=2,
        max_length=200,
    )
    description: str | None = None
    synonyms: list[str] = []
    business_owner: str | None = Field(
        default=None,
        max_length=150,
    )
    classification: Classification = "internal"
    ai_access_allowed: bool = True
    confidence: int = Field(
        default=0,
        ge=0,
        le=100,
    )


class BusinessEntityUpdate(BaseModel):
    domain_id: int | None = None
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )
    description: str | None = None
    synonyms: list[str] | None = None
    business_owner: str | None = Field(
        default=None,
        max_length=150,
    )
    classification: Classification | None = None
    ai_access_allowed: bool | None = None
    approval_status: ApprovalStatus | None = None
    confidence: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    is_active: bool | None = None


class BusinessEntityResponse(BaseModel):
    id: int
    domain_id: int
    name: str
    description: str | None
    synonyms: str | None
    business_owner: str | None
    classification: str
    ai_access_allowed: bool
    approval_status: str
    confidence: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    table_mappings: list[
        EntityTableMappingResponse
    ] = []

    model_config = ConfigDict(from_attributes=True)


class BusinessEntitySuggestionResponse(BaseModel):
    metadata_table_id: int
    suggested_domain_name: str
    suggested_entity_name: str
    description: str
    synonyms: list[str]
    confidence: int
    reasons: list[str]
