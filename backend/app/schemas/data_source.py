from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DatabaseType = Literal[
    "postgresql",
    "mysql",
    "oracle",
]


class DataSourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=50)
    database_type: DatabaseType
    host: str = Field(min_length=1, max_length=150)
    port: int = Field(gt=0, le=65535)
    database_name: str | None = None
    service_name: str | None = None
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=500)
    description: str | None = None
    is_active: bool = True


class DataSourceUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    port: int | None = Field(default=None, gt=0, le=65535)
    database_name: str | None = None
    service_name: str | None = None
    username: str | None = None
    password: str | None = None
    description: str | None = None
    is_active: bool | None = None


class DataSourceResponse(BaseModel):
    id: int
    name: str
    code: str
    database_type: str
    host: str
    port: int
    database_name: str | None
    service_name: str | None
    username: str
    description: str | None
    status: str
    is_active: bool
    last_test_message: str | None
    last_tested_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConnectionTestResponse(BaseModel):
    success: bool
    status: str
    message: str
