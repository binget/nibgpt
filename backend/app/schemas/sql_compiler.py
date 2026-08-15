from typing import Any, Literal

from pydantic import BaseModel, Field


SupportedDialect = Literal[
    "mysql",
    "postgresql",
    "oracle",
    "mssql",
]


class SQLCompilerRequest(BaseModel):
    prompt: str = Field(
        min_length=2,
        max_length=2000,
    )

    domain_id: int | None = None

    requested_limit: int = Field(
        default=100,
        ge=1,
        le=1000,
    )

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

    user_role: str = Field(
        default="standard_user",
        min_length=2,
        max_length=100,
    )


class CompiledParameterResponse(BaseModel):
    name: str
    value: Any
    data_type: str


class CompiledTableResponse(BaseModel):
    metadata_table_id: int
    data_source_id: int
    schema_name: str | None
    table_name: str
    alias: str


class CompiledJoinResponse(BaseModel):
    join_mapping_id: int
    relationship_id: int

    join_type: str

    source_table_alias: str
    source_column_name: str

    target_table_alias: str
    target_column_name: str

    expression: str


class SQLCompilerResponse(BaseModel):
    prompt: str

    decision: str
    is_compiled: bool

    dialect: SupportedDialect | None

    sql: str | None

    parameters: list[
        CompiledParameterResponse
    ]

    tables: list[
        CompiledTableResponse
    ]

    joins: list[
        CompiledJoinResponse
    ]

    approved_limit: int

    overall_confidence: int

    warnings: list[str]
    errors: list[str]
    explanation: list[str]
