import json

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.ai.entity_suggester import (
    suggest_business_entity,
)
from app.database.session import get_db
from app.models.business_entity import (
    BusinessDomain,
    BusinessEntity,
    BusinessEntityTableMap,
)
from app.models.data_source import DataSource
from app.models.metadata import MetadataTable
from app.schemas.business_entity import (
    BusinessDomainCreate,
    BusinessDomainResponse,
    BusinessDomainUpdate,
    BusinessEntityCreate,
    BusinessEntityResponse,
    BusinessEntitySuggestionResponse,
    BusinessEntityUpdate,
    EntityTableMappingCreate,
    EntityTableMappingResponse,
)


router = APIRouter(
    prefix="/api/business-entities",
    tags=["Business Entity Registry"],
)


@router.get(
    "/domains",
    response_model=list[
        BusinessDomainResponse
    ],
)
def list_domains(
    database: Session = Depends(get_db),
):
    statement = (
        select(BusinessDomain)
        .order_by(BusinessDomain.name)
    )

    return list(
        database.scalars(statement).all()
    )


@router.post(
    "/domains",
    response_model=BusinessDomainResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_domain(
    payload: BusinessDomainCreate,
    database: Session = Depends(get_db),
):
    domain = BusinessDomain(
        **payload.model_dump()
    )

    database.add(domain)

    try:
        database.commit()
        database.refresh(domain)

        return domain

    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A business domain with this name already exists.",
        ) from error


@router.put(
    "/domains/{domain_id}",
    response_model=BusinessDomainResponse,
)
def update_domain(
    domain_id: int,
    payload: BusinessDomainUpdate,
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

    for field_name, value in payload.model_dump(
        exclude_unset=True
    ).items():
        setattr(
            domain,
            field_name,
            value,
        )

    try:
        database.commit()
        database.refresh(domain)

        return domain

    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A business domain with this name already exists.",
        ) from error


@router.get(
    "",
    response_model=list[
        BusinessEntityResponse
    ],
)
def list_entities(
    domain_id: int | None = None,
    database: Session = Depends(get_db),
):
    statement = (
        select(BusinessEntity)
        .options(
            selectinload(
                BusinessEntity.table_mappings
            )
        )
    )

    if domain_id is not None:
        statement = statement.where(
            BusinessEntity.domain_id
            == domain_id
        )

    statement = statement.order_by(
        BusinessEntity.name
    )

    return list(
        database.scalars(statement).all()
    )


@router.post(
    "",
    response_model=BusinessEntityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_entity(
    payload: BusinessEntityCreate,
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

    values = payload.model_dump()
    synonyms = values.pop("synonyms")

    entity = BusinessEntity(
        **values,
        synonyms=json.dumps(synonyms),
    )

    database.add(entity)

    try:
        database.commit()

        statement = (
            select(BusinessEntity)
            .options(
                selectinload(
                    BusinessEntity.table_mappings
                )
            )
            .where(
                BusinessEntity.id == entity.id
            )
        )

        return database.scalar(statement)

    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This business entity already exists in the selected domain.",
        ) from error


@router.put(
    "/{entity_id}",
    response_model=BusinessEntityResponse,
)
def update_entity(
    entity_id: int,
    payload: BusinessEntityUpdate,
    database: Session = Depends(get_db),
):
    entity = database.get(
        BusinessEntity,
        entity_id,
    )

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found",
        )

    values = payload.model_dump(
        exclude_unset=True
    )

    if "synonyms" in values:
        values["synonyms"] = json.dumps(
            values["synonyms"]
        )

    for field_name, value in values.items():
        setattr(
            entity,
            field_name,
            value,
        )

    database.commit()

    statement = (
        select(BusinessEntity)
        .options(
            selectinload(
                BusinessEntity.table_mappings
            )
        )
        .where(
            BusinessEntity.id == entity_id
        )
    )

    return database.scalar(statement)


@router.post(
    "/{entity_id}/table-mappings",
    response_model=EntityTableMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_table_mapping(
    entity_id: int,
    payload: EntityTableMappingCreate,
    database: Session = Depends(get_db),
):
    entity = database.get(
        BusinessEntity,
        entity_id,
    )

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity not found",
        )

    table = database.get(
        MetadataTable,
        payload.metadata_table_id,
    )

    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metadata table not found",
        )

    mapping = BusinessEntityTableMap(
        business_entity_id=entity_id,
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
            detail="This table is already mapped to the business entity.",
        ) from error


@router.delete(
    "/table-mappings/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_table_mapping(
    mapping_id: int,
    database: Session = Depends(get_db),
):
    mapping = database.get(
        BusinessEntityTableMap,
        mapping_id,
    )

    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business entity table mapping not found",
        )

    database.delete(mapping)
    database.commit()


@router.get(
    "/suggestions/from-table/{table_id}",
    response_model=BusinessEntitySuggestionResponse,
)
def suggest_entity_from_table(
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

    source = database.get(
        DataSource,
        table.data_source_id,
    )

    source_name = (
        source.name
        if source
        else "Connected Business System"
    )

    return suggest_business_entity(
        table=table,
        source_name=source_name,
    )
