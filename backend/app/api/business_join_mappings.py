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
    selectinload,
)

from app.ai.join_mapping_suggester import (
    suggest_join_mapping,
)
from app.database.session import get_db
from app.models.business_entity import (
    BusinessEntity,
)
from app.models.business_join_mapping import (
    BusinessRelationshipJoinMapping,
)
from app.models.business_relationship import (
    BusinessEntityRelationship,
)
from app.models.metadata import (
    MetadataColumn,
    MetadataTable,
)
from app.schemas.business_join_mapping import (
    BusinessJoinMappingCreate,
    BusinessJoinMappingResponse,
    BusinessJoinMappingSuggestionResponse,
    BusinessJoinMappingUpdate,
)

from app.ai.auto_join_mapper import (
    create_auto_join_mapping,
    resolve_relationship_join,
)


router = APIRouter(
    prefix="/api/business-join-mappings",
    tags=["Physical Join Mapping Registry"],
)


def join_mapping_statement():
    return (
        select(
            BusinessRelationshipJoinMapping
        )
        .options(
            joinedload(
                BusinessRelationshipJoinMapping
                .source_table
            ),
            joinedload(
                BusinessRelationshipJoinMapping
                .source_column
            ),
            joinedload(
                BusinessRelationshipJoinMapping
                .target_table
            ),
            joinedload(
                BusinessRelationshipJoinMapping
                .target_column
            ),
        )
    )


def get_mapping_or_404(
    database: Session,
    mapping_id: int,
) -> BusinessRelationshipJoinMapping:
    statement = (
        join_mapping_statement()
        .where(
            BusinessRelationshipJoinMapping.id
            == mapping_id
        )
    )

    mapping = database.scalar(
        statement
    )

    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical join mapping not found",
        )

    return mapping


def get_entity_table_ids(
    entity: BusinessEntity,
) -> set[int]:
    return {
        mapping.metadata_table_id
        for mapping in entity.table_mappings
        if mapping.is_active
    }


def validate_join_mapping(
    database: Session,
    payload: BusinessJoinMappingCreate,
) -> tuple[
    BusinessEntityRelationship,
    MetadataTable,
    MetadataColumn,
    MetadataTable,
    MetadataColumn,
]:
    relationship = database.get(
        BusinessEntityRelationship,
        payload.relationship_id,
    )

    if relationship is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business relationship not found",
        )

    if (
        relationship.approval_status
        != "approved"
        or not relationship.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The semantic relationship must be "
                "approved and active before a physical "
                "join can be configured."
            ),
        )

    source_entity_statement = (
        select(BusinessEntity)
        .options(
            selectinload(
                BusinessEntity.table_mappings
            )
        )
        .where(
            BusinessEntity.id
            == relationship.source_entity_id
        )
    )

    target_entity_statement = (
        select(BusinessEntity)
        .options(
            selectinload(
                BusinessEntity.table_mappings
            )
        )
        .where(
            BusinessEntity.id
            == relationship.target_entity_id
        )
    )

    source_entity = database.scalar(
        source_entity_statement
    )

    target_entity = database.scalar(
        target_entity_statement
    )

    if (
        source_entity is None
        or target_entity is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Source or target business entity "
                "was not found."
            ),
        )

    # --------------------------------------------------
    # Load physical tables and columns FIRST
    # --------------------------------------------------

    source_table = database.get(
        MetadataTable,
        payload.source_metadata_table_id,
    )

    target_table = database.get(
        MetadataTable,
        payload.target_metadata_table_id,
    )

    source_column = database.get(
        MetadataColumn,
        payload.source_metadata_column_id,
    )

    target_column = database.get(
        MetadataColumn,
        payload.target_metadata_column_id,
    )

    if (
        source_table is None
        or target_table is None
        or source_column is None
        or target_column is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "One or more selected metadata "
                "tables or columns were not found."
            ),
        )

    # --------------------------------------------------
    # Now it is safe to validate self-joins
    # --------------------------------------------------

    if (
        relationship.source_entity_id
        != relationship.target_entity_id
        and source_table.id
        == target_table.id
        and source_column.id
        == target_column.id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A relationship between different "
                "business entities cannot join the "
                "same physical table column to itself."
            ),
        )

    source_table_ids = get_entity_table_ids(
        source_entity
    )

    target_table_ids = get_entity_table_ids(
        target_entity
    )

    if (
        source_table.id
        not in source_table_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The source table is not mapped to "
                "the source business entity."
            ),
        )

    if (
        target_table.id
        not in target_table_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The target table is not mapped to "
                "the target business entity."
            ),
        )

    if (
        source_column.metadata_table_id
        != source_table.id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The source column does not belong "
                "to the selected source table."
            ),
        )

    if (
        target_column.metadata_table_id
        != target_table.id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The target column does not belong "
                "to the selected target table."
            ),
        )

    if (
        source_table.data_source_id
        != target_table.data_source_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cross-data-source physical joins "
                "are not supported in this version."
            ),
        )

    if (
        not source_table.is_discovered
        or not source_table.is_enabled
        or not source_table.ai_access_allowed
        or not target_table.is_discovered
        or not target_table.is_enabled
        or not target_table.ai_access_allowed
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Both physical tables must be enabled, "
                "discovered and approved for AI access."
            ),
        )

    if (
        not source_column.is_discovered
        or not source_column.is_enabled
        or not source_column.ai_access_allowed
        or not target_column.is_discovered
        or not target_column.is_enabled
        or not target_column.ai_access_allowed
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Both join columns must be enabled, "
                "discovered and approved for AI access."
            ),
        )

    return (
        relationship,
        source_table,
        source_column,
        target_table,
        target_column,
    )


@router.get(
    "",
    response_model=list[
        BusinessJoinMappingResponse
    ],
)
def list_join_mappings(
    relationship_id: int | None = None,
    approval_status: str | None = None,
    database: Session = Depends(get_db),
):
    statement = join_mapping_statement()

    if relationship_id is not None:
        statement = statement.where(
            BusinessRelationshipJoinMapping
            .relationship_id
            == relationship_id
        )

    if approval_status:
        statement = statement.where(
            BusinessRelationshipJoinMapping
            .approval_status
            == approval_status
        )

    statement = statement.order_by(
        BusinessRelationshipJoinMapping.id
    )

    return list(
        database.scalars(
            statement
        ).unique().all()
    )


@router.post(
    "",
    response_model=BusinessJoinMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_join_mapping(
    payload: BusinessJoinMappingCreate,
    database: Session = Depends(get_db),
):
    validate_join_mapping(
        database,
        payload,
    )

    mapping = (
        BusinessRelationshipJoinMapping(
            **payload.model_dump()
        )
    )

    database.add(mapping)

    try:
        database.commit()

        return get_mapping_or_404(
            database,
            mapping.id,
        )

    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This physical join mapping "
                "already exists."
            ),
        ) from error


@router.put(
    "/{mapping_id}",
    response_model=BusinessJoinMappingResponse,
)
def update_join_mapping(
    mapping_id: int,
    payload: BusinessJoinMappingUpdate,
    database: Session = Depends(get_db),
):
    mapping = get_mapping_or_404(
        database,
        mapping_id,
    )

    values = payload.model_dump(
        exclude_unset=True
    )

    for field_name, value in values.items():
        setattr(
            mapping,
            field_name,
            value,
        )

    database.commit()

    return get_mapping_or_404(
        database,
        mapping_id,
    )


@router.delete(
    "/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_join_mapping(
    mapping_id: int,
    database: Session = Depends(get_db),
):
    mapping = database.get(
        BusinessRelationshipJoinMapping,
        mapping_id,
    )

    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical join mapping not found",
        )

    database.delete(mapping)
    database.commit()


@router.get(
    "/suggest/{relationship_id}",
    response_model=BusinessJoinMappingSuggestionResponse,
)
def suggest_join_mapping_for_relationship(
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

    source_entity_statement = (
        select(BusinessEntity)
        .options(
            selectinload(
                BusinessEntity.table_mappings
            )
        )
        .where(
            BusinessEntity.id
            == relationship.source_entity_id
        )
    )

    target_entity_statement = (
        select(BusinessEntity)
        .options(
            selectinload(
                BusinessEntity.table_mappings
            )
        )
        .where(
            BusinessEntity.id
            == relationship.target_entity_id
        )
    )

    source_entity = database.scalar(
        source_entity_statement
    )

    target_entity = database.scalar(
        target_entity_statement
    )

    if source_entity is None or target_entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Source or target business entity "
                "was not found."
            ),
        )

    source_table_ids = get_entity_table_ids(
        source_entity
    )

    target_table_ids = get_entity_table_ids(
        target_entity
    )

    source_column_statement = (
        select(MetadataColumn)
        .where(
            MetadataColumn.metadata_table_id.in_(
                source_table_ids
            ),
            MetadataColumn.is_discovered.is_(
                True
            ),
            MetadataColumn.is_enabled.is_(
                True
            ),
            MetadataColumn.ai_access_allowed.is_(
                True
            ),
        )
    )

    target_column_statement = (
        select(MetadataColumn)
        .where(
            MetadataColumn.metadata_table_id.in_(
                target_table_ids
            ),
            MetadataColumn.is_discovered.is_(
                True
            ),
            MetadataColumn.is_enabled.is_(
                True
            ),
            MetadataColumn.ai_access_allowed.is_(
                True
            ),
        )
    )

    source_columns = list(
        database.scalars(
            source_column_statement
        ).all()
    )

    target_columns = list(
        database.scalars(
            target_column_statement
        ).all()
    )

    suggestion = suggest_join_mapping(
        relationship_id=relationship.id,
        source_columns=source_columns,
        target_columns=target_columns,
    )

    if suggestion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No compatible join-column suggestion "
                "could be generated."
            ),
        )

    return suggestion


@router.get(
    "/auto-resolve/{relationship_id}"
)
def auto_resolve_join(
    relationship_id: int,
    database: Session = Depends(
        get_db
    ),
):
    result = resolve_relationship_join(
        database=database,
        relationship_id=(
            relationship_id
        ),
    )

    candidate = result.candidate

    return {
        "relationship_id": (
            result.relationship_id
        ),

        "status": result.status,

        "message": result.message,

        "can_auto_approve": (
            result.can_auto_approve
        ),

        "existing_mapping_id": (
            result.existing_mapping.id
            if result.existing_mapping
            else None
        ),

        "best_candidate": (
            {
                "confidence": (
                    candidate.confidence
                ),

                "score": (
                    candidate.score
                ),

                "source_table": {
                    "id": (
                        candidate
                        .source_table
                        .id
                    ),
                    "name": (
                        candidate
                        .source_table
                        .table_name
                    ),
                },

                "source_column": {
                    "id": (
                        candidate
                        .source_column
                        .id
                    ),
                    "name": (
                        candidate
                        .source_column
                        .column_name
                    ),
                    "business_name": (
                        candidate
                        .source_column
                        .business_name
                    ),
                },

                "target_table": {
                    "id": (
                        candidate
                        .target_table
                        .id
                    ),
                    "name": (
                        candidate
                        .target_table
                        .table_name
                    ),
                },

                "target_column": {
                    "id": (
                        candidate
                        .target_column
                        .id
                    ),
                    "name": (
                        candidate
                        .target_column
                        .column_name
                    ),
                    "business_name": (
                        candidate
                        .target_column
                        .business_name
                    ),
                },

                "reasons": (
                    candidate.reasons
                ),
            }
            if candidate
            else None
        ),

        "alternative_candidates": [
            {
                "confidence": item.confidence,

                "source": (
                    f"{item.source_table.table_name}."
                    f"{item.source_column.column_name}"
                ),

                "target": (
                    f"{item.target_table.table_name}."
                    f"{item.target_column.column_name}"
                ),
            }
            for item
            in result.candidates[
                1:5
            ]
        ],
    }


@router.post(
    "/auto-resolve/{relationship_id}"
)
def auto_create_join(
    relationship_id: int,
    auto_approve: bool = True,
    database: Session = Depends(
        get_db
    ),
):
    (
        resolution,
        mapping,
    ) = create_auto_join_mapping(
        database=database,
        relationship_id=(
            relationship_id
        ),
        auto_approve=(
            auto_approve
        ),
    )

    return {
        "relationship_id": (
            relationship_id
        ),

        "resolution_status": (
            resolution.status
        ),

        "message": (
            resolution.message
        ),

        "can_auto_approve": (
            resolution.can_auto_approve
        ),

        "mapping_created": (
            mapping is not None
        ),

        "mapping_id": (
            mapping.id
            if mapping
            else None
        ),

        "approval_status": (
            mapping.approval_status
            if mapping
            else None
        ),

        "confidence": (
            mapping.confidence
            if mapping
            else (
                resolution
                .candidate
                .confidence
                if resolution.candidate
                else None
            )
        ),

        "physical_join": (
            {
                "source": (
                    f"{resolution.candidate.source_table.table_name}."
                    f"{resolution.candidate.source_column.column_name}"
                ),

                "target": (
                    f"{resolution.candidate.target_table.table_name}."
                    f"{resolution.candidate.target_column.column_name}"
                ),
            }
            if resolution.candidate
            else None
        ),
    }
