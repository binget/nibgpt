import json

from typing import (
    Any,
)

from fastapi import (
    APIRouter,
    Depends,
)

from fastapi.responses import (
    StreamingResponse,
)

from pydantic import (
    BaseModel,
    Field,
)

from sqlalchemy import (
    select,
)

from sqlalchemy.orm import (
    Session,
)

from app.ai.general_agent import (
    stream_general_answer,
)

from app.database.session import (
    get_db,
)

from app.models.conversation import (
    ChatMessage,
    Conversation,
)

from app.ai.report_explainer import (
    stream_report_explanation,
)

from app.ai.document_intelligence import (
    stream_document_question,
)

from app.core.auth_dependencies import (
    get_current_user,
)

from app.models.user import (
    User,
)

from app.services.authorization_service import (
    resolve_authorization_requirement,
)

from app.services.rbac_service import (
    authorize_request,
)


router = APIRouter(
    prefix="/api/orchestrator",
    tags=["NIBGPT Streaming"],
)


class StreamRequest(BaseModel):
    prompt: str = Field(
        min_length=1,
        max_length=5000,
    )

    conversation_id: int | None = None

    mode: str = "general"
    
class ReportExplanationRequest(
    BaseModel
):
    report: dict[str, Any]

def event_message(
    event_type: str,
    **data,
) -> str:
    payload = {
        "type": event_type,
        **data,
    }

    return (
        f"data: "
        f"{json.dumps(payload)}"
        f"\n\n"
    )


def load_conversation_history(
    database: Session,
    conversation_id: int | None,
    current_prompt: str,
    current_user: User,
    
) -> list[dict[str, str]]:
    if conversation_id is None:
        return []

    conversation = database.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )

    if conversation is None:
        return []

    statement = (
        select(
            ChatMessage
        )
        .where(
            ChatMessage.conversation_id
            == conversation_id
        )
        .order_by(
            ChatMessage.created_at.desc()
        )
        .limit(8)
    )

    messages = list(
        database
        .scalars(
            statement
        )
        .all()
    )

    # Query was newest first.
    messages.reverse()

    history: list[
        dict[str, str]
    ] = []

    for message in messages:
        role = (
            message.role
            .strip()
            .lower()
        )

        if role not in {
            "user",
            "assistant",
        }:
            continue

        content = (
            message.content
            .strip()
        )

        if not content:
            continue

        history.append(
            {
                "role": role,
                "content": content,
            }
        )

    # --------------------------------------------------
    # The frontend saves the current user message before
    # calling /stream.
    #
    # Therefore the final history item may already be
    # exactly the prompt we're about to send.
    #
    # Remove it so the model does not see:
    #
    # User: Give me an example
    # User: Give me an example
    # --------------------------------------------------

    if history:
        last_message = history[-1]

        if (
            last_message["role"]
            == "user"
            and
            last_message["content"]
            .strip()
            == current_prompt.strip()
        ):
            history.pop()

    return history


@router.post(
    "/stream"
)
def stream_nibgpt(
    payload: StreamRequest,
    database: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    route = (
        "knowledge"
        if payload.mode in (
            "document",
            "knowledge",
        )
        else "general"
    )

    authorization = (
        resolve_authorization_requirement(
            prompt=payload.prompt,
            route=route,
        )
    )

    authorize_request(
        database=database,
        user=current_user,
        permission_code=(
            authorization.permission_code
        ),
        resource=(
            authorization.resource
        ),
        request_text=payload.prompt,
    )
    history = (
        load_conversation_history(
            database=database,
            conversation_id=(
                payload.conversation_id
            ),
            current_prompt=(
                payload.prompt
            ),
        )
    )

    def generate():
        try:
            yield event_message(
                "start"
            )

            if payload.mode in (
                "document",
                "knowledge",
            ):

                token_stream = (
                    stream_document_question(
                        database=database,
                        question=payload.prompt,
                    )
                )

            else:

                token_stream = (
                    stream_general_answer(
                        prompt=payload.prompt,
                        history=history,
                    )
                )

            for token in token_stream:

                yield event_message(
                    "token",
                    content=token,
                )

            yield event_message(
                "done"
            )

        except Exception as error:
            yield event_message(
                "error",
                message=str(error),
            )

    return StreamingResponse(
        generate(),
        media_type=(
            "text/event-stream"
        ),
        headers={
            "Cache-Control":
                "no-cache",
            "X-Accel-Buffering":
                "no",
        },
    )
    
@router.post(
    "/report-explanation/stream"
)
def stream_report_explanation_api(
    payload: ReportExplanationRequest,
):
    def generate():
        try:
            yield event_message(
                "start"
            )

            for token in (
                stream_report_explanation(
                    payload.report
                )
            ):
                yield event_message(
                    "token",
                    content=token,
                )

            yield event_message(
                "done"
            )

        except Exception as error:
            yield event_message(
                "error",
                message=str(error),
            )

    return StreamingResponse(
        generate(),
        media_type=(
            "text/event-stream"
        ),
        headers={
            "Cache-Control":
                "no-cache",
            "X-Accel-Buffering":
                "no",
        },
    )
    
