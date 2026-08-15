from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.ai.capability_suggester import (
    suggest_capability,
)
from app.database.session import get_db
from app.models.business_capability import (
    BusinessCapability,
    BusinessCapabilityEntityMap,
)
from app.models.business_entity import (
    BusinessDomain,
    BusinessEntity,
)
from app.schemas.business_capability import (
    BusinessCapabilityCreate,
    BusinessCapabilityResponse,
    BusinessCapabilityUpdate,
    CapabilityEntityMappingCreate,
    CapabilityEntityMappingResponse,
    CapabilitySuggestionResponse,
)


router = APIRouter(
    prefix="/api/business-capabilities",
    tags=["Business Capability Registry"],
)


def capability_statement():
    return (
        select(BusinessCapability)
        .options(
            selectinload(
                BusinessCapability.entity_mappings
            )
        )
    )


def get_capability_or_404(
    database: Session,
    capability_id: int,
) -> BusinessCapability:
    statement = (
        capability_statement()
        .where(
            BusinessCapability.id
            == capability_id
        )
    )

    capability = database.scalar(
        statement
    )

    if capability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business capability not found",
        )

    return capability


@router.get(
    "",
    response_model=list[
        BusinessCapabilityResponse
    ],
)
def list_capabilities(
    domain_id: int | None = None,
    approval_status: str | None = None,
    database: Session = Depends(get_db),
):
    statement = capability_statement()

    if domain_id is not None:
        statement = statement.where(
            BusinessCapability.domain_id
            == domain_id
        )

    if approval_status:
        statement = statement.where(
            BusinessCapability.approval_status
            == approval_status
        )

    statement = statement.order_by(
        BusinessCapability.name
    )

    return list(
        database.scalars(
            statement
        ).unique().all()
    )


@router.post(
    "",
    response_model=BusinessCapabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_capability(
    payload: BusinessCapabilityCreate,
    database: Session = Depends(get_db),
):
    domain = database.get(
        BusinessDomain,
        payload.domain_id,
    )

    if domain is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business domain not found",
        )

    if payload.parent_capability_id:
        parent = database.get(
            BusinessCapability,
            payload.parent_capability_id,
        )

        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Parent business capability "
                    "not found"
                ),
            )

        if parent.domain_id != payload.domain_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Parent capability must belong "
                    "to the same business domain."
                ),
            )

    capability = BusinessCapability(
        **payload.model_dump()
    )

    database.add(capability)

    try:
        database.commit()

        return get_capability_or_404(
            database,
            capability.id,
        )

    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A capability with this name "
                "already exists in the selected "
                "business domain."
            ),
        ) from error


@router.put(
    "/{capability_id}",
    response_model=BusinessCapabilityResponse,
)
def update_capability(
    capability_id: int,
    payload: BusinessCapabilityUpdate,
    database: Session = Depends(get_db),
):
    capability = get_capability_or_404(
        database,
        capability_id,
    )

    values = payload.model_dump(
        exclude_unset=True
    )

    new_domain_id = values.get(
        "domain_id",
        capability.domain_id,
    )

    parent_id = values.get(
        "parent_capability_id",
        capability.parent_capability_id,
    )

    if parent_id == capability_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A capability cannot be its "
                "own parent."
            ),
        )

    if parent_id:
        parent = database.get(
            BusinessCapability,
            parent_id,
        )

        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Parent business capability "
                    "not found"
                ),
            )

        if parent.domain_id != new_domain_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Parent capability must belong "
                    "to the same business domain."
                ),
            )

    for field_name, value in values.items():
        setattr(
            capability,
            field_name,
            value,
        )

    try:
        database.commit()

        return get_capability_or_404(
            database,
            capability_id,
        )

    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A capability with this name "
                "already exists in the selected "
                "business domain."
            ),
        ) from error


@router.delete(
    "/{capability_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_capability(
    capability_id: int,
    database: Session = Depends(get_db),
):
    capability = database.get(
        BusinessCapability,
        capability_id,
    )

    if capability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business capability not found",
        )

    database.delete(capability)
    database.commit()


@router.post(
    "/{capability_id}/entity-mappings",
    response_model=CapabilityEntityMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_entity_mapping(
    capability_id: int,
    payload: CapabilityEntityMappingCreate,
    database: Session = Depends(get_db),
):
    capability = database.get(
        BusinessCapability,
        capability_id,
    )

    if capability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business capability not found",
        )

    entity = database.get(
        BusinessEntity,
        payload.business_entity_id,
    )

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found",
        )

    if (
        entity.domain_id
        != capability.domain_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The business entity and capability "
                "must belong to the same domain."
            ),
        )

    mapping = BusinessCapabilityEntityMap(
        capability_id=capability_id,
        **payload.model_dump(),
    )

    database.add(mapping)

    try:
        database.commit()
        database.refresh(mapping)

        return mapping

    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This entity is already mapped "
                "to the business capability."
            ),
        ) from error


@router.delete(
    "/entity-mappings/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_entity_mapping(
    mapping_id: int,
    database: Session = Depends(get_db),
):
    mapping = database.get(
        BusinessCapabilityEntityMap,
        mapping_id,
    )

    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Capability entity mapping "
                "not found"
            ),
        )

    database.delete(mapping)
    database.commit()


@router.get(
    "/suggest",
    response_model=CapabilitySuggestionResponse,
)
def suggest_business_capability(
    domain_id: int,
    entity_ids: list[int] = Query(
        default=[],
    ),
    database: Session = Depends(get_db),
):
    domain = database.get(
        BusinessDomain,
        domain_id,
    )

    if domain is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business domain not found",
        )

    entities: list[BusinessEntity] = []

    if entity_ids:
        statement = (
            select(BusinessEntity)
            .options(
                selectinload(
                    BusinessEntity.table_mappings
                )
            )
            .where(
                BusinessEntity.id.in_(
                    entity_ids
                )
            )
        )

        entities = list(
            database.scalars(
                statement
            ).unique().all()
        )

        if len(entities) != len(
            set(entity_ids)
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "One or more selected business "
                    "entities were not found."
                ),
            )

        invalid_entities = [
            entity.name
            for entity in entities
            if entity.domain_id != domain_id
        ]

        if invalid_entities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "All selected entities must "
                    "belong to the selected domain."
                ),
            )

    return suggest_capability(
        domain_id=domain_id,
        entities=entities,
    )
