import json

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.dictionary_generator import (
    generate_table_definition,
)
from app.database.session import get_db
from app.models.metadata import MetadataTable
from app.schemas.metadata import (
    DefinitionApprovalRequest,
    GeneratedTableDefinition,
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
    "/tables/{table_id}/generate-definition",
    response_model=GeneratedTableDefinition,
)
def generate_definition(
    table_id: int,
    database: Session = Depends(get_db),
):
    table = get_table_with_columns(
        database,
        table_id,
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
    table = get_table_with_columns(
        database,
        table_id,
    )

    generated = generate_table_definition(
        table
    )

    table.business_name = generated["business_name"]
    table.description = generated["description"]
    table.synonyms = json.dumps(
        generated["synonyms"]
    )
    table.suggested_questions = json.dumps(
        generated["suggested_questions"]
    )
    table.definition_status = "generated"

    generated_columns = {
        item["column_id"]: item
        for item in generated["columns"]
    }

    for column in table.columns:
        generated_column = generated_columns.get(
            column.id
        )

        if generated_column is None:
            continue

        column.business_name = generated_column[
            "business_name"
        ]
        column.description = generated_column[
            "description"
        ]
        column.synonyms = json.dumps(
            generated_column["synonyms"]
        )
        column.classification = generated_column[
            "classification"
        ]
        column.is_sensitive = generated_column[
            "is_sensitive"
        ]
        column.definition_status = "generated"

    database.commit()

    return get_table_with_columns(
        database,
        table_id,
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
    table = get_table_with_columns(
        database,
        table_id,
    )

    status_value = (
        "approved"
        if payload.approved
        else "rejected"
    )

    table.definition_status = status_value

    for column in table.columns:
        column.definition_status = status_value

    database.commit()

    return get_table_with_columns(
        database,
        table_id,
    )
