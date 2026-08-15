from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.orm import Session

from app.ai.sql_compiler import (
    create_and_compile_sql,
)
from app.database.session import get_db
from app.schemas.sql_compiler import (
    CompiledJoinResponse,
    CompiledParameterResponse,
    CompiledTableResponse,
    SQLCompilerRequest,
    SQLCompilerResponse,
)


router = APIRouter(
    prefix="/api/sql-compiler",
    tags=["Semantic SQL Compiler"],
)


@router.post(
    "/compile",
    response_model=SQLCompilerResponse,
)
def compile_semantic_sql(
    payload: SQLCompilerRequest,
    database: Session = Depends(
        get_db
    ),
):
    result = create_and_compile_sql(
        database=database,
        prompt=payload.prompt.strip(),
        domain_id=payload.domain_id,
        requested_limit=(
            payload.requested_limit
        ),
        maximum_entities=(
            payload.maximum_entities
        ),
        maximum_path_depth=(
            payload.maximum_path_depth
        ),
        user_role=(
            payload.user_role
        ),
    )

    return SQLCompilerResponse(
        prompt=result.prompt,
        decision=result.decision,
        is_compiled=(
            result.is_compiled
        ),
        dialect=result.dialect,
        sql=result.sql,
        parameters=[
            CompiledParameterResponse(
                name=item.name,
                value=item.value,
                data_type=(
                    item.data_type
                ),
            )
            for item
            in result.parameters
        ],
        tables=[
            CompiledTableResponse(
                metadata_table_id=(
                    item.metadata_table_id
                ),
                data_source_id=(
                    item.data_source_id
                ),
                schema_name=(
                    item.schema_name
                ),
                table_name=(
                    item.table_name
                ),
                alias=item.alias,
            )
            for item
            in result.tables
        ],
        joins=[
            CompiledJoinResponse(
                join_mapping_id=(
                    item.join_mapping_id
                ),
                relationship_id=(
                    item.relationship_id
                ),
                join_type=(
                    item.join_type
                ),
                source_table_alias=(
                    item.source_table_alias
                ),
                source_column_name=(
                    item.source_column_name
                ),
                target_table_alias=(
                    item.target_table_alias
                ),
                target_column_name=(
                    item.target_column_name
                ),
                expression=(
                    item.expression
                ),
            )
            for item
            in result.joins
        ],
        approved_limit=(
            result.approved_limit
        ),
        overall_confidence=(
            result.overall_confidence
        ),
        warnings=result.warnings,
        errors=result.errors,
        explanation=(
            result.explanation
        ),
    )
