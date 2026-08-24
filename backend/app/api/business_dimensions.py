from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.database.session import get_db

from app.models.business_entity import (
    BusinessEntity,
)

from app.models.business_dimension import (
    BusinessDimension,
)

from app.models.metadata import (
    MetadataColumn,
)

from app.schemas.business_dimension import (
    BusinessDimensionCreate,
    BusinessDimensionResponse,
    BusinessDimensionUpdate,
)


router = APIRouter(
    prefix="/api/business-dimensions",
    tags=["Business Dimension Registry"],
)


def business_dimension_statement():
    return (
        select(
            BusinessDimension
        )
        .options(
            joinedload(
                BusinessDimension.entity
            ),
            joinedload(
                BusinessDimension.column
            ),
        )
    )


def validate_business_dimension(
    database: Session,
    business_entity_id: int,
    metadata_column_id: int,
):
    entity = database.get(
        BusinessEntity,
        business_entity_id,
    )

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Business entity was not found."
            ),
        )

    if (
        entity.approval_status != "approved"
        or not entity.is_active
        or not entity.ai_access_allowed
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Business dimensions can only be "
                "created for approved, active and "
                "AI-accessible entities."
            ),
        )

    column = database.get(
        MetadataColumn,
        metadata_column_id,
    )

    if column is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Metadata column was not found."
            ),
        )

    if (
        not column.is_discovered
        or not column.is_enabled
        or not column.ai_access_allowed
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The selected metadata column must "
                "be discovered, enabled and approved "
                "for AI access."
            ),
        )

    mapped_table_ids = {
        mapping.metadata_table_id
        for mapping
        in entity.table_mappings
        if mapping.is_active
    }

    if (
        column.metadata_table_id
        not in mapped_table_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The selected metadata column does "
                "not belong to a table mapped to "
                "this business entity."
            ),
        )

    return (
        entity,
        column,
    )


@router.get(
    "",
    response_model=list[
        BusinessDimensionResponse
    ],
)
def list_business_dimensions(
    business_entity_id: int | None = None,
    approval_status: str | None = None,
    is_active: bool | None = None,
    database: Session = Depends(
        get_db
    ),
):
    statement = (
        business_dimension_statement()
    )

    if business_entity_id is not None:
        statement = statement.where(
            BusinessDimension.business_entity_id
            == business_entity_id
        )

    if approval_status:
        statement = statement.where(
            BusinessDimension.approval_status
            == approval_status
        )

    if is_active is not None:
        statement = statement.where(
            BusinessDimension.is_active
            .is_(is_active)
        )

    statement = statement.order_by(
        BusinessDimension.name
    )

    return list(
        database.scalars(
            statement
        ).unique().all()
    )


@router.get(
    "/{dimension_id}",
    response_model=BusinessDimensionResponse,
)
def get_business_dimension(
    dimension_id: int,
    database: Session = Depends(
        get_db
    ),
):
    statement = (
        business_dimension_statement()
        .where(
            BusinessDimension.id
            == dimension_id
        )
    )

    dimension = database.scalar(
        statement
    )

    if dimension is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Business dimension not found"
            ),
        )

    return dimension


@router.post(
    "",
    response_model=BusinessDimensionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_business_dimension(
    payload: BusinessDimensionCreate,
    database: Session = Depends(
        get_db
    ),
):
    (
        entity,
        column,
    ) = validate_business_dimension(
        database=database,
        business_entity_id=(
            payload.business_entity_id
        ),
        metadata_column_id=(
            payload.metadata_column_id
        ),
    )

    dimension = BusinessDimension(
        business_entity_id=(
            payload.business_entity_id
        ),
        metadata_column_id=(
            payload.metadata_column_id
        ),
        name=payload.name.strip(),
        trigger_phrases=(
            payload.trigger_phrases
        ),
        synonyms=payload.synonyms,
        description=payload.description,
        confidence=payload.confidence,
        approval_status=(
            payload.approval_status
        ),
        is_active=payload.is_active,
    )

    database.add(
        dimension
    )

    try:
        database.commit()

        statement = (
            business_dimension_statement()
            .where(
                BusinessDimension.id
                == dimension.id
            )
        )

        return database.scalar(
            statement
        )

    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This business dimension "
                "already exists."
            ),
        ) from error


@router.put(
    "/{dimension_id}",
    response_model=BusinessDimensionResponse,
)
def update_business_dimension(
    dimension_id: int,
    payload: BusinessDimensionUpdate,
    database: Session = Depends(
        get_db
    ),
):
    dimension = database.get(
        BusinessDimension,
        dimension_id,
    )

    if dimension is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Business dimension not found"
            ),
        )

    values = payload.model_dump(
        exclude_unset=True
    )

    new_entity_id = values.get(
        "business_entity_id",
        dimension.business_entity_id,
    )

    new_column_id = values.get(
        "metadata_column_id",
        dimension.metadata_column_id,
    )

    (
        entity,
        column,
    ) = validate_business_dimension(
        database=database,
        business_entity_id=new_entity_id,
        metadata_column_id=new_column_id,
    )

    if (
        "name" in values
        and values["name"] is not None
    ):
        values["name"] = (
            values["name"].strip()
        )

    for field_name, value in (
        values.items()
    ):
        setattr(
            dimension,
            field_name,
            value,
        )

    try:
        database.commit()

        statement = (
            business_dimension_statement()
            .where(
                BusinessDimension.id
                == dimension_id
            )
        )

        return database.scalar(
            statement
        )

    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This business dimension "
                "already exists."
            ),
        ) from error


@router.delete(
    "/{dimension_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_business_dimension(
    dimension_id: int,
    database: Session = Depends(
        get_db
    ),
):
    dimension = database.get(
        BusinessDimension,
        dimension_id,
    )

    if dimension is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Business dimension not found"
            ),
        )

    database.delete(
        dimension
    )

    database.commit()

    return None