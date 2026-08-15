import json

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.knowledge_builder import (
    build_knowledge_profile,
)
from app.database.session import get_db
from app.models.metadata import MetadataTable
from app.schemas.metadata import (
    GeneratedKnowledgeProfile,
    KnowledgeApprovalRequest,
    MetadataTableDetailResponse,
)


router = APIRouter()


def get_table_with_columns(
    database: Session,
    table_id: int,
) -> MetadataTable:
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


@router.post(
    "/tables/{table_id}/generate-knowledge",
    response_model=GeneratedKnowledgeProfile,
)
def generate_knowledge_profile(
    table_id: int,
    database: Session = Depends(get_db),
):
    table = get_table_with_columns(
        database,
        table_id,
    )

    return build_knowledge_profile(table)


@router.post(
    "/tables/{table_id}/apply-knowledge",
    response_model=MetadataTableDetailResponse,
)
def apply_knowledge_profile(
    table_id: int,
    database: Session = Depends(get_db),
):
    table = get_table_with_columns(
        database,
        table_id,
    )

    generated = build_knowledge_profile(table)

    table.business_purpose = generated[
        "business_purpose"
    ]

    table.business_terms = json.dumps(
        generated["business_terms"]
    )

    table.suggested_questions = json.dumps(
        generated["common_questions"]
    )

    table.common_filters = json.dumps(
        generated["common_filters"]
    )

    table.common_measures = json.dumps(
        generated["common_measures"]
    )

    table.primary_business_keys = json.dumps(
        generated["primary_business_keys"]
    )

    table.related_entities = json.dumps(
        generated["related_entities"]
    )

    table.ai_notes = generated["ai_notes"]
    table.knowledge_status = "generated"

    database.commit()

    return get_table_with_columns(
        database,
        table_id,
    )


@router.post(
    "/tables/{table_id}/approve-knowledge",
    response_model=MetadataTableDetailResponse,
)
def approve_knowledge_profile(
    table_id: int,
    payload: KnowledgeApprovalRequest,
    database: Session = Depends(get_db),
):
    table = get_table_with_columns(
        database,
        table_id,
    )

    table.knowledge_status = (
        "approved"
        if payload.approved
        else "rejected"
    )

    database.commit()

    return get_table_with_columns(
        database,
        table_id,
    )
