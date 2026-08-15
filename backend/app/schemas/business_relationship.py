from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RelationshipType = Literal[
    "business",
    "reference",
    "dependency",
    "hierarchical",
    "process",
]


Cardinality = Literal[
    "one_to_one",
    "one_to_many",
    "many_to_one",
    "many_to_many",
]


ApprovalStatus = Literal[
    "draft",
    "generated",
    "approved",
    "rejected",
]


class BusinessRelationshipCreate(BaseModel):
    source_entity_id: int
    target_entity_id: int

    relationship_name: str = Field(
        min_length=2,
        max_length=120,
    )

    inverse_relationship_name: str | None = Field(
        default=None,
        max_length=120,
    )

    relationship_type: RelationshipType = "business"
    cardinality: Cardinality = "many_to_one"

    description: str | None = None

    confidence: int = Field(
        default=0,
        ge=0,
        le=100,
    )


class BusinessRelationshipUpdate(BaseModel):
    relationship_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
    )

    inverse_relationship_name: str | None = Field(
        default=None,
        max_length=120,
    )

    relationship_type: RelationshipType | None = None
    cardinality: Cardinality | None = None
    description: str | None = None

    confidence: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    approval_status: ApprovalStatus | None = None
    is_active: bool | None = None


class RelationshipEntitySummary(BaseModel):
    id: int
    domain_id: int
    name: str
    description: str | None
    classification: str
    approval_status: str

    model_config = ConfigDict(
        from_attributes=True
    )


class BusinessRelationshipResponse(BaseModel):
    id: int

    source_entity_id: int
    target_entity_id: int

    relationship_name: str
    inverse_relationship_name: str | None

    relationship_type: str
    cardinality: str
    description: str | None

    confidence: int
    approval_status: str
    is_active: bool

    created_at: datetime
    updated_at: datetime

    source_entity: RelationshipEntitySummary
    target_entity: RelationshipEntitySummary

    model_config = ConfigDict(
        from_attributes=True
    )


class RelationshipSuggestionResponse(BaseModel):
    source_entity_id: int
    target_entity_id: int

    relationship_name: str
    inverse_relationship_name: str | None

    relationship_type: str
    cardinality: str

    description: str
    confidence: int
    reasons: list[str]
