from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.encryption import encrypt_value
from app.database.session import get_db
from app.models.data_source import DataSource
from app.schemas.data_source import (
    ConnectionTestResponse,
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
)
from app.services.data_source_tester import test_data_source


router = APIRouter(
    prefix="/api/data-sources",
    tags=["Data Sources"],
)


@router.get(
    "",
    response_model=list[DataSourceResponse],
)
def list_data_sources(
    database: Session = Depends(get_db),
):
    statement = select(DataSource).order_by(
        DataSource.created_at.desc()
    )

    return list(database.scalars(statement).all())


@router.get(
    "/{source_id}",
    response_model=DataSourceResponse,
)
def get_data_source(
    source_id: int,
    database: Session = Depends(get_db),
):
    source = database.get(DataSource, source_id)

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    return source


@router.post(
    "",
    response_model=DataSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_data_source(
    payload: DataSourceCreate,
    database: Session = Depends(get_db),
):
    source = DataSource(
        name=payload.name,
        code=payload.code.upper().strip(),
        database_type=payload.database_type,
        host=payload.host.strip(),
        port=payload.port,
        database_name=payload.database_name,
        service_name=payload.service_name,
        username=payload.username,
        encrypted_password=encrypt_value(payload.password),
        description=payload.description,
        is_active=payload.is_active,
    )

    database.add(source)

    try:
        database.commit()
        database.refresh(source)
    except IntegrityError:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Data-source code already exists",
        )

    return source


@router.put(
    "/{source_id}",
    response_model=DataSourceResponse,
)
def update_data_source(
    source_id: int,
    payload: DataSourceUpdate,
    database: Session = Depends(get_db),
):
    source = database.get(DataSource, source_id)

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    values = payload.model_dump(
        exclude_unset=True,
    )

    password = values.pop("password", None)

    for field_name, value in values.items():
        setattr(source, field_name, value)

    if password:
        source.encrypted_password = encrypt_value(password)

    source.status = "not_tested"
    source.last_test_message = None

    database.commit()
    database.refresh(source)

    return source


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_data_source(
    source_id: int,
    database: Session = Depends(get_db),
):
    source = database.get(DataSource, source_id)

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    database.delete(source)
    database.commit()


@router.post(
    "/{source_id}/test",
    response_model=ConnectionTestResponse,
)
def test_connection(
    source_id: int,
    database: Session = Depends(get_db),
):
    source = database.get(DataSource, source_id)

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    try:
        test_data_source(source)

        source.status = "connected"
        source.last_test_message = "Connection successful"

        result = ConnectionTestResponse(
            success=True,
            status="connected",
            message="Connection successful",
        )

    except Exception as error:
        source.status = "failed"
        source.last_test_message = str(error)[:500]

        result = ConnectionTestResponse(
            success=False,
            status="failed",
            message=str(error),
        )

    source.last_tested_at = datetime.utcnow()

    database.commit()

    return result
