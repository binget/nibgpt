from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.metadata import MetadataColumn, MetadataTable

from app.database.session import get_db
from app.models.data_source import DataSource

from app.schemas.metadata import (
    MetadataColumnResponse,
    MetadataColumnUpdate,
    MetadataScanResponse,
    MetadataTableDetailResponse,
    MetadataTableSummaryResponse,
    MetadataTableUpdate,
    GeneratedTableDefinition,
    DefinitionApprovalRequest,
)
from app.services.metadata_scanner import (
    scan_data_source_metadata,
)

import json
from app.ai.dictionary_generator import (
    generate_table_definition,
)


router = APIRouter(
    prefix="/api/metadata",
    tags=["Metadata Catalogue"],
)


@router.post(
    "/data-sources/{source_id}/scan",
    response_model=MetadataScanResponse,
)
def scan_metadata(
    source_id: int,
    database: Session = Depends(get_db),
):
    source = database.get(
        DataSource,
        source_id,
    )

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    if not source.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data source is inactive",
        )

    if source.status != "connected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Test the data-source connection "
                "successfully before scanning metadata"
            ),
        )

    try:
        result = scan_data_source_metadata(
            database=database,
            source=source,
        )

        return MetadataScanResponse(
            success=True,
            data_source_id=source.id,
            schemas_scanned=(
                result.schemas_scanned
            ),
            tables_discovered=(
                result.tables_discovered
            ),
            views_discovered=(
                result.views_discovered
            ),
            columns_discovered=(
                result.columns_discovered
            ),
            message=(
                "Metadata discovery completed "
                "successfully"
            ),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Metadata scan failed: "
                f"{str(error)}"
            ),
        ) from error


@router.get(
    "/tables",
    response_model=list[
        MetadataTableSummaryResponse
    ],
)
def list_metadata_tables(
    data_source_id: int | None = None,
    search: str | None = Query(
        default=None,
        max_length=100,
    ),
    database: Session = Depends(get_db),
):
    statement = select(MetadataTable)

    if data_source_id is not None:
        statement = statement.where(
            MetadataTable.data_source_id
            == data_source_id
        )

    if search:
        search_term = f"%{search.strip()}%"

        statement = statement.where(
            or_(
                MetadataTable.table_name.ilike(
                    search_term
                ),
                MetadataTable.business_name.ilike(
                    search_term
                ),
                MetadataTable.description.ilike(
                    search_term
                ),
            )
        )

    statement = statement.order_by(
        MetadataTable.schema_name,
        MetadataTable.table_name,
    )

    return list(
        database.scalars(statement).all()
    )


@router.get(
    "/tables/{table_id}",
    response_model=MetadataTableDetailResponse,
)
def get_metadata_table(
    table_id: int,
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

    return table


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

    for field_name, value in values.items():
        setattr(table, field_name, value)

    database.commit()

    updated_statement = (
        select(MetadataTable)
        .options(
            selectinload(MetadataTable.columns)
        )
        .where(
            MetadataTable.id == table_id
        )
    )

    updated_table = database.scalar(
        updated_statement
    )

    return updated_table


@router.post(
    "/tables/{table_id}/generate-definition",
    response_model=GeneratedTableDefinition,
)
def generate_definition(
    table_id: int,
    database: Session = Depends(get_db),
):
    statement = (
        select(MetadataTable)
        .options(
            selectinload(
                MetadataTable.columns
            )
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

    return generate_table_definition(table)


@router.post(
    "/tables/{table_id}/apply-generated-definition",
    response_model=MetadataTableDetailResponse,
)
def apply_generated_definition(
    table_id: int,
    database: Session = Depends(get_db),
):
    statement = (
        select(MetadataTable)
        .options(
            selectinload(
                MetadataTable.columns
            )
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

    generated = generate_table_definition(
        table
    )

    table.business_name = (
        generated["business_name"]
    )
    table.description = (
        generated["description"]
    )
    table.synonyms = json.dumps(
        generated["synonyms"]
    )
    table.suggested_questions = (
        json.dumps(
            generated[
                "suggested_questions"
            ]
        )
    )
    table.definition_status = "generated"

    generated_columns = {
        item["column_id"]: item
        for item in generated["columns"]
    }

    for column in table.columns:
        generated_column = (
            generated_columns.get(
                column.id
            )
        )

        if not generated_column:
            continue

        column.business_name = (
            generated_column[
                "business_name"
            ]
        )
        column.description = (
            generated_column[
                "description"
            ]
        )
        column.synonyms = json.dumps(
            generated_column[
                "synonyms"
            ]
        )
        column.classification = (
            generated_column[
                "classification"
            ]
        )
        column.is_sensitive = (
            generated_column[
                "is_sensitive"
            ]
        )
        column.definition_status = (
            "generated"
        )

    database.commit()

    refreshed_statement = (
        select(MetadataTable)
        .options(
            selectinload(
                MetadataTable.columns
            )
        )
        .where(
            MetadataTable.id == table_id
        )
    )

    return database.scalar(
        refreshed_statement
    )


@router.post(
    "/tables/{table_id}/approve-definition",
    response_model=MetadataTableDetailResponse,
)
def approve_definition(
    table_id: int,
    payload: DefinitionApprovalRequest,
    database: Session = Depends(get_db),
):
    statement = (
        select(MetadataTable)
        .options(
            selectinload(
                MetadataTable.columns
            )
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

    table.definition_status = (
        "approved"
        if payload.approved
        else "rejected"
    )

    for column in table.columns:
        column.definition_status = (
            "approved"
            if payload.approved
            else "rejected"
        )

    database.commit()

    refreshed_statement = (
        select(MetadataTable)
        .options(
            selectinload(
                MetadataTable.columns
            )
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

    values = payload.model_dump(exclude_unset=True)

    for field_name, value in values.items():
        setattr(column, field_name, value)

    database.commit()
    database.refresh(column)

    return column

    table = database.scalar(statement)

    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metadata table not found",
        )

    return table
