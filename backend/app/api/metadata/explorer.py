from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models.data_source import DataSource
from app.models.metadata import MetadataTable
from app.schemas.metadata import (
    MetadataScanResponse,
    MetadataTableDetailResponse,
    MetadataTableSummaryResponse,
)
from app.services.metadata_scanner import (
    scan_data_source_metadata,
)


router = APIRouter()


@router.post(
    "/data-sources/{source_id}/scan",
    response_model=MetadataScanResponse,
)
def scan_metadata(
    source_id: int,
    database: Session = Depends(get_db),
):
    source = database.get(DataSource, source_id)

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
                "Test the data-source connection successfully "
                "before scanning metadata"
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

    new_tables=result.new_tables,
    updated_tables=result.updated_tables,
    removed_tables=result.removed_tables,

    new_columns=result.new_columns,
    updated_columns=result.updated_columns,
    removed_columns=result.removed_columns,

    message=(
        "Incremental metadata discovery "
        "completed successfully"
    ),
)

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Metadata scan failed: {str(error)}",
        ) from error


@router.get(
    "/tables",
    response_model=list[MetadataTableSummaryResponse],
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
            MetadataTable.data_source_id == data_source_id
        )

    if search:
        search_term = f"%{search.strip()}%"

        statement = statement.where(
            or_(
                MetadataTable.table_name.ilike(search_term),
                MetadataTable.business_name.ilike(search_term),
                MetadataTable.description.ilike(search_term),
                MetadataTable.synonyms.ilike(search_term),
            )
        )

    statement = statement.order_by(
        MetadataTable.schema_name,
        MetadataTable.table_name,
    )

    return list(database.scalars(statement).all())


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
