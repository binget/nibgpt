from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.ai.relationship_suggester import (
    suggest_relationship,
)
from app.database.session import get_db
from app.models.business_entity import (
    BusinessEntity,
)
from app.models.business_relationship import (
    BusinessEntityRelationship,
)
from app.schemas.business_relationship import (
    BusinessRelationshipCreate,
    BusinessRelationshipResponse,
    BusinessRelationshipUpdate,
    RelationshipSuggestionResponse,
)


router = APIRouter(
    prefix="/api/business-relationships",
    tags=["Business Relationship Registry"],
)


def relationship_statement():
    return select(
        BusinessEntityRelationship
    ).options(
        joinedload(
            BusinessEntityRelationship.source_entity
        ),
        joinedload(
            BusinessEntityRelationship.target_entity
        ),
    )


@router.get(
    "",
    response_model=list[
        BusinessRelationshipResponse
    ],
)
def list_relationships(
    entity_id: int | None = None,
    approval_status: str | None = None,
    database: Session = Depends(get_db),
):
    statement = relationship_statement()

    if entity_id is not None:
        statement = statement.where(
            or_(
                BusinessEntityRelationship.source_entity_id
                == entity_id,
                BusinessEntityRelationship.target_entity_id
                == entity_id,
            )
        )

    if approval_status:
        statement = statement.where(
            BusinessEntityRelationship.approval_status
            == approval_status
        )

    statement = statement.order_by(
        BusinessEntityRelationship.relationship_name
    )

    return list(
        database.scalars(
            statement
        ).unique().all()
    )


@router.post(
    "",
    response_model=BusinessRelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_relationship(
    payload: BusinessRelationshipCreate,
    database: Session = Depends(get_db),
):
    if (
        payload.source_entity_id
        == payload.target_entity_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "An entity cannot have a relationship "
                "with itself."
            ),
        )

    source = database.get(
        BusinessEntity,
        payload.source_entity_id,
    )

    target = database.get(
        BusinessEntity,
        payload.target_entity_id,
    )

    if source is None or target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Source or target business entity "
                "was not found."
            ),
        )

    relationship = BusinessEntityRelationship(
        **payload.model_dump()
    )

    database.add(relationship)

    try:
        database.commit()

        statement = (
            relationship_statement()
            .where(
                BusinessEntityRelationship.id
                == relationship.id
            )
        )

        return database.scalar(statement)

    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This business relationship "
                "already exists."
            ),
        ) from error


@router.put(
    "/{relationship_id}",
    response_model=BusinessRelationshipResponse,
)
def update_relationship(
    relationship_id: int,
    payload: BusinessRelationshipUpdate,
    database: Session = Depends(get_db),
):
    relationship = database.get(
        BusinessEntityRelationship,
        relationship_id,
    )

    if relationship is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business relationship not found",
        )

    values = payload.model_dump(
        exclude_unset=True
    )

    for field_name, value in values.items():
        setattr(
            relationship,
            field_name,
            value,
        )

    database.commit()

    statement = (
        relationship_statement()
        .where(
            BusinessEntityRelationship.id
            == relationship_id
        )
    )

    return database.scalar(statement)


@router.delete(
    "/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_relationship(
    relationship_id: int,
    database: Session = Depends(get_db),
):
    relationship = database.get(
        BusinessEntityRelationship,
        relationship_id,
    )

    if relationship is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business relationship not found",
        )

    database.delete(relationship)
    database.commit()


@router.get(
    "/suggest",
    response_model=RelationshipSuggestionResponse,
)
def suggest_entity_relationship(
    source_entity_id: int,
    target_entity_id: int,
    database: Session = Depends(get_db),
):
    if source_entity_id == target_entity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Source and target entities "
                "must be different."
            ),
        )

    source = database.get(
        BusinessEntity,
        source_entity_id,
    )

    target = database.get(
        BusinessEntity,
        target_entity_id,
    )

    if source is None or target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Source or target business entity "
                "was not found."
            ),
        )

    return suggest_relationship(
        source=source,
        target=target,
    )
