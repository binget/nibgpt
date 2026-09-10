from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from pydantic import BaseModel, Field

from sqlalchemy import select
from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.database.session import (
    get_db,
)

from app.models.conversation import (
    ChatMessage,
    Conversation,
)

from app.schemas.chat import (
    ConversationDetailResponse,
    ConversationSummaryResponse,
)

from app.core.auth_dependencies import get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/api/chat",
    tags=["AI Workspace"],
)


# ============================================================
# Request schemas
# ============================================================


class CreateConversationRequest(
    BaseModel
):
    first_prompt: str = Field(
        min_length=1,
        max_length=5000,
    )


class SaveMessageRequest(
    BaseModel
):
    role: str = Field(
        min_length=1,
        max_length=20,
    )

    content: str = Field(
        min_length=1,
    )

    source_type: str | None = None
    
    report_payload: dict | None = None

class RenameConversationRequest(
    BaseModel
):
    title: str = Field(
        min_length=1,
        max_length=200,
    )
# ============================================================
# Helpers
# ============================================================


def create_title(
    prompt: str,
) -> str:
    cleaned = " ".join(
        prompt.split()
    )

    if len(cleaned) <= 60:
        return cleaned

    return (
        cleaned[:57]
        + "..."
    )


def get_or_404(
    database: Session,
    conversation_id: int,
    current_user: User,
) -> Conversation:
    statement = (
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )

    conversation = database.scalar(statement)

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return conversation


# ============================================================
# List conversations
# ============================================================


@router.get(
    "/conversations",
    response_model=list[
        ConversationSummaryResponse
    ],
)
def list_conversations(
    database: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Conversation)
        .where(
            Conversation.user_id == current_user.id
        )
        .order_by(
            Conversation.updated_at.desc()
        )
    )

    return list(
        database.scalars(statement).all()
    )


# ============================================================
# Get one conversation
# ============================================================


@router.get(
    "/conversations/{conversation_id}",
    response_model=(
        ConversationDetailResponse
    ),
)
def get_conversation(
    conversation_id: int,
    database: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Conversation)
        .options(
            selectinload(
                Conversation.messages
            )
        )
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )

    conversation = database.scalar(statement)

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return conversation


# ============================================================
# Create conversation
# ============================================================


@router.post(
    "/conversations",
    response_model=(
        ConversationSummaryResponse
    ),
)
def create_conversation(
    payload: CreateConversationRequest,
    database: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    first_prompt = (
        payload
        .first_prompt
        .strip()
    )

    conversation = Conversation(
        user_id=current_user.id,
        title=create_title(
            first_prompt
        ),
    )

    database.add(
        conversation
    )

    database.commit()

    database.refresh(
        conversation
    )

    return conversation


# ============================================================
# Save message
#
# This endpoint DOES NOT generate AI.
#
# NIBGPTPage does:
#
# user prompt
# -> orchestrator
# -> reporting / knowledge / stream
#
# Then this endpoint stores the result.
# ============================================================


@router.post(
    "/conversations/{conversation_id}/messages",
)
def save_message(
    conversation_id: int,
    payload: SaveMessageRequest,
    database: Session = Depends(
        get_db
    ),
    current_user: User = Depends(get_current_user),
):
    conversation = get_or_404(
        database=database,
        conversation_id=conversation_id,
        current_user=current_user,
    )

    role = (
        payload
        .role
        .strip()
        .lower()
    )

    if role not in {
        "user",
        "assistant",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "Role must be "
                "'user' or 'assistant'."
            ),
        )

    content = (
        payload
        .content
        .strip()
    )

    if not content:
        raise HTTPException(
            status_code=400,
            detail=(
                "Message content "
                "cannot be empty."
            ),
        )

    message = ChatMessage(
    conversation_id=conversation.id,
    role=role,
    content=content,
    source_type=payload.source_type,
    report_payload=(
        payload.report_payload
    ),
)

    database.add(
        message
    )

    conversation.updated_at = (
        datetime.utcnow()
    )

    database.commit()
    database.refresh(
        message
    )

    return {
        "id": message.id,
        "conversation_id": (
            message.conversation_id
        ),
        "role": message.role,
        "content": message.content,
        "source_type": (
            message.source_type
        ),
        "report_payload": (
            message.report_payload
        ),
        "created_at": (
            message.created_at
        ),
    }
    
    
# ============================================================
# Rename conversation
# ============================================================


@router.patch(
    "/conversations/{conversation_id}",
    response_model=(
        ConversationSummaryResponse
    ),
)
def rename_conversation(
    conversation_id: int,
    payload: RenameConversationRequest,
    database: Session = Depends(
        get_db
    ),
    current_user: User = Depends(get_current_user),
):
    conversation = get_or_404(
        database=database,
        conversation_id=conversation_id,
        current_user=current_user,
    )

    title = (
        " ".join(
            payload
            .title
            .split()
        )
    )

    if not title:
        raise HTTPException(
            status_code=400,
            detail=(
                "Conversation title "
                "cannot be empty."
            ),
        )

    conversation.title = title
    conversation.updated_at = (
        datetime.utcnow()
    )

    database.commit()
    database.refresh(
        conversation
    )

    return conversation


# ============================================================
# Delete conversation
# ============================================================


@router.delete(
    "/conversations/{conversation_id}",
    status_code=(
        status.HTTP_204_NO_CONTENT
    ),
)
def delete_conversation(
    conversation_id: int,
    database: Session = Depends(
        get_db
    ),
    current_user: User = Depends(get_current_user),
):
    conversation = get_or_404(
        database=database,
        conversation_id=conversation_id,
        current_user=current_user,
    )

    database.delete(
        conversation
    )

    database.commit()