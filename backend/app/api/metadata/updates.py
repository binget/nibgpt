from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models.metadata import (
    MetadataColumn,
    MetadataTable,
)
from app.schemas.metadata import (
    MetadataColumnResponse,
    MetadataColumnUpdate,
    MetadataTableDetailResponse,
    MetadataTableUpdate,
)


router = APIRouter()


@router.put(
    "/tables/{table_id}",
    response_model=MetadataTableDetailResponse,
)
def update_metadata_table(
    table_id: int,
    payload: MetadataTableUpdate,
    database: Session = Depends(get_db),
):
    statement = (
        select(MetadataTable)
        .options(
            selectinload(MetadataTable.columns)
        )
        .where(
            MetadataTable.id == table_id
        )
    )

    table = database.scalar(statement)

    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metadata table not found",
        )

    values = payload.model_dump(
        exclude_unset=True
    )

    print(values)

    for field_name, value in values.items():
        setattr(table, field_name, value)

    database.commit()

    refreshed_statement = (
        select(MetadataTable)
        .options(
            selectinload(MetadataTable.columns)
        )
        .where(
            MetadataTable.id == table_id
        )
    )

    return database.scalar(
        refreshed_statement
    )


@router.put(
    "/columns/{column_id}",
    response_model=MetadataColumnResponse,
)
def update_metadata_column(
    column_id: int,
    payload: MetadataColumnUpdate,
    database: Session = Depends(get_db),
):
    column = database.get(
        MetadataColumn,
        column_id,
    )

    if column is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metadata column not found",
        )

    values = payload.model_dump(
        exclude_unset=True
    )

    for field_name, value in values.items():
        setattr(column, field_name, value)

    database.commit()
    database.refresh(column)

    return column
