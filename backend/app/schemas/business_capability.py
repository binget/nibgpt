from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


CapabilityType = Literal[
    "strategic",
    "core",
    "operational",
    "supporting",
    "control",
]

MaturityLevel = Literal[
    "initial",
    "developing",
    "defined",
    "managed",
    "optimized",
]

ApprovalStatus = Literal[
    "draft",
    "generated",
    "approved",
    "rejected",
]

EntityMappingRole = Literal[
    "primary",
    "supporting",
    "reference",
    "output",
]


class BusinessCapabilityCreate(BaseModel):
    domain_id: int

    parent_capability_id: int | None = None

    name: str = Field(
        min_length=2,
        max_length=200,
    )

    description: str | None = None

    business_owner: str | None = Field(
        default=None,
        max_length=150,
    )

    capability_type: CapabilityType = "operational"

    maturity_level: MaturityLevel = "developing"

    confidence: int = Field(
        default=0,
        ge=0,
        le=100,
    )


class BusinessCapabilityUpdate(BaseModel):
    domain_id: int | None = None

    parent_capability_id: int | None = None

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    description: str | None = None

    business_owner: str | None = Field(
        default=None,
        max_length=150,
    )

    capability_type: CapabilityType | None = None

    maturity_level: MaturityLevel | None = None

    approval_status: ApprovalStatus | None = None

    confidence: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    is_active: bool | None = None


class CapabilityEntityMappingCreate(BaseModel):
    business_entity_id: int

    mapping_role: EntityMappingRole = "primary"

    confidence: int = Field(
        default=100,
        ge=0,
        le=100,
    )


class CapabilityEntityMappingResponse(BaseModel):
    id: int
    capability_id: int
    business_entity_id: int
    mapping_role: str
    confidence: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class BusinessCapabilityResponse(BaseModel):
    id: int
    domain_id: int
    parent_capability_id: int | None

    name: str
    description: str | None
    business_owner: str | None

    capability_type: str
    maturity_level: str
    approval_status: str

    confidence: int
    is_active: bool

    created_at: datetime
    updated_at: datetime

    entity_mappings: list[
        CapabilityEntityMappingResponse
    ] = []

    model_config = ConfigDict(
        from_attributes=True
    )


class CapabilitySuggestionResponse(BaseModel):
    domain_id: int
    suggested_name: str
    description: str
    capability_type: str
    maturity_level: str

    suggested_entity_ids: list[int]

    confidence: int
    reasons: list[str]
