from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from app.ai.query_executor import (
    execute_governed_prompt,
)

from app.database.session import (
    get_db,
)

from app.schemas.query_executor import (
    QueryExecutionRequest,
    QueryExecutionResponse,
)


router = APIRouter(
    prefix="/api/query-executor",
    tags=["NIBGPT Query Executor"],
)


@router.post(
    "/execute",
    response_model=(
        QueryExecutionResponse
    ),
)
def execute_query(
    payload: QueryExecutionRequest,
    database: Session = Depends(
        get_db
    ),
):
    try:
        return execute_governed_prompt(
            database=database,
            prompt=payload.prompt.strip(),
            domain_id=(
                payload.domain_id
            ),
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

    except ValueError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "The governed query could not "
                "be executed: "
                f"{error}"
            ),
        ) from error