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

from app.models.business_measure import (
    BusinessMeasure,
)

from app.models.metadata import (
    MetadataColumn,
)

from app.schemas.business_measure import (
    BusinessMeasureCreate,
    BusinessMeasureResponse,
    BusinessMeasureUpdate,
)


router = APIRouter(
    prefix="/api/business-measures",
    tags=["Business Measure Registry"],
)


ALLOWED_AGGREGATIONS = {
    "count",
    "sum",
    "average",
    "minimum",
    "maximum",
}


def business_measure_statement():
    return (
        select(
            BusinessMeasure
        )
        .options(
            joinedload(
                BusinessMeasure.entity
            ),
            joinedload(
                BusinessMeasure.column
            ),
        )
    )


def validate_business_measure(
    database: Session,
    business_entity_id: int,
    metadata_column_id: int | None,
    aggregation_function: str,
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
                "Business measures can only be "
                "created for approved, active and "
                "AI-accessible entities."
            ),
        )

    normalized_function = (
        aggregation_function
        .strip()
        .lower()
    )

    if (
        normalized_function
        not in ALLOWED_AGGREGATIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported aggregation function."
            ),
        )

    # COUNT(*) does not require a physical column.
    if (
        normalized_function == "count"
        and metadata_column_id is None
    ):
        return (
            entity,
            None,
            normalized_function,
        )

    if metadata_column_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{normalized_function} measures "
                "require a metadata column."
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
        normalized_function,
    )


@router.get(
    "",
    response_model=list[
        BusinessMeasureResponse
    ],
)
def list_business_measures(
    business_entity_id: int | None = None,
    approval_status: str | None = None,
    is_active: bool | None = None,
    database: Session = Depends(
        get_db
    ),
):
    statement = (
        business_measure_statement()
    )

    if business_entity_id is not None:
        statement = statement.where(
            BusinessMeasure.business_entity_id
            == business_entity_id
        )

    if approval_status:
        statement = statement.where(
            BusinessMeasure.approval_status
            == approval_status
        )

    if is_active is not None:
        statement = statement.where(
            BusinessMeasure.is_active
            .is_(is_active)
        )

    statement = statement.order_by(
        BusinessMeasure.name
    )

    return list(
        database.scalars(
            statement
        ).unique().all()
    )


@router.get(
    "/{measure_id}",
    response_model=BusinessMeasureResponse,
)
def get_business_measure(
    measure_id: int,
    database: Session = Depends(
        get_db
    ),
):
    statement = (
        business_measure_statement()
        .where(
            BusinessMeasure.id
            == measure_id
        )
    )

    measure = database.scalar(
        statement
    )

    if measure is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business measure not found",
        )

    return measure


@router.post(
    "",
    response_model=BusinessMeasureResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_business_measure(
    payload: BusinessMeasureCreate,
    database: Session = Depends(
        get_db
    ),
):
    (
        entity,
        column,
        normalized_function,
    ) = validate_business_measure(
        database=database,
        business_entity_id=(
            payload.business_entity_id
        ),
        metadata_column_id=(
            payload.metadata_column_id
        ),
        aggregation_function=(
            payload.aggregation_function
        ),
    )

    measure = BusinessMeasure(
        business_entity_id=(
            payload.business_entity_id
        ),
        metadata_column_id=(
            payload.metadata_column_id
        ),
        name=payload.name.strip(),
        aggregation_function=(
            normalized_function
        ),
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
        measure
    )

    try:
        database.commit()

        statement = (
            business_measure_statement()
            .where(
                BusinessMeasure.id
                == measure.id
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
                "This business measure "
                "already exists."
            ),
        ) from error


@router.put(
    "/{measure_id}",
    response_model=BusinessMeasureResponse,
)
def update_business_measure(
    measure_id: int,
    payload: BusinessMeasureUpdate,
    database: Session = Depends(
        get_db
    ),
):
    measure = database.get(
        BusinessMeasure,
        measure_id,
    )

    if measure is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business measure not found",
        )

    values = payload.model_dump(
        exclude_unset=True
    )

    new_entity_id = values.get(
        "business_entity_id",
        measure.business_entity_id,
    )

    new_column_id = values.get(
        "metadata_column_id",
        measure.metadata_column_id,
    )

    new_function = values.get(
        "aggregation_function",
        measure.aggregation_function,
    )

    (
        entity,
        column,
        normalized_function,
    ) = validate_business_measure(
        database=database,
        business_entity_id=new_entity_id,
        metadata_column_id=new_column_id,
        aggregation_function=new_function,
    )

    if (
        "name" in values
        and values["name"] is not None
    ):
        values["name"] = (
            values["name"].strip()
        )

    values[
        "aggregation_function"
    ] = normalized_function

    for field_name, value in (
        values.items()
    ):
        setattr(
            measure,
            field_name,
            value,
        )

    try:
        database.commit()

        statement = (
            business_measure_statement()
            .where(
                BusinessMeasure.id
                == measure_id
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
                "This business measure "
                "already exists."
            ),
        ) from error


@router.delete(
    "/{measure_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_business_measure(
    measure_id: int,
    database: Session = Depends(
        get_db
    ),
):
    measure = database.get(
        BusinessMeasure,
        measure_id,
    )

    if measure is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business measure not found",
        )

    database.delete(
        measure
    )

    database.commit()

    return None