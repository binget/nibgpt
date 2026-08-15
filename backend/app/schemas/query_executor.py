from typing import Any

from pydantic import BaseModel, Field


class QueryExecutionRequest(BaseModel):
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
        le=20,
    )

    maximum_path_depth: int = Field(
        default=4,
        ge=1,
        le=10,
    )

    user_role: str = "analyst"


class QueryExecutionResponse(BaseModel):
    success: bool

    prompt: str
    decision: str

    data_source_id: int | None = None
    data_source_name: str | None = None

    sql: str | None = None

    answer: str | None = None

    parameters: dict[
        str,
        Any,
    ] = {}

    columns: list[str] = []

    rows: list[
        dict[str, Any]
    ] = []

    row_count: int = 0

    execution_time_ms: float | None = None

    warnings: list[str] = []
    errors: list[str] = []
    explanation: list[str] = []