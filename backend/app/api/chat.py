from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.engine import generate_nibgpt_response
from app.database.session import get_db
from app.models.conversation import ChatMessage, Conversation
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    ConversationSummaryResponse,
)


router = APIRouter(
    prefix="/api/chat",
    tags=["AI Workspace"],
)


def create_title(prompt: str) -> str:
    cleaned = " ".join(prompt.split())

    if len(cleaned) <= 60:
        return cleaned

    return cleaned[:57] + "..."


@router.get(
    "/conversations",
    response_model=list[ConversationSummaryResponse],
)
def list_conversations(
    database: Session = Depends(get_db),
):
    statement = select(Conversation).order_by(
        Conversation.updated_at.desc()
    )

    return list(database.scalars(statement).all())


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def get_conversation(
    conversation_id: int,
    database: Session = Depends(get_db),
):
    statement = (
        select(Conversation)
        .options(
            selectinload(Conversation.messages)
        )
        .where(
            Conversation.id == conversation_id
        )
    )

    conversation = database.scalar(statement)

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return conversation


@router.post(
    "/message",
    response_model=ChatResponse,
)
def send_message(
    payload: ChatRequest,
    database: Session = Depends(get_db),
):
    prompt = payload.prompt.strip()

    if payload.conversation_id is None:
        conversation = Conversation(
            title=create_title(prompt)
        )

        database.add(conversation)
        database.flush()

    else:
        conversation = database.get(
            Conversation,
            payload.conversation_id,
        )

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

    user_message = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content=prompt,
        source_type="user",
    )

    database.add(user_message)
    database.flush()

    response_text, source_type = generate_nibgpt_response(
        database=database,
        prompt=prompt,
    )

    assistant_message = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text,
        source_type=source_type,
    )

    database.add(assistant_message)

    conversation.updated_at = datetime.utcnow()

    database.commit()
    database.refresh(assistant_message)

    return ChatResponse(
        conversation_id=conversation.id,
        message=assistant_message,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conversation(
    conversation_id: int,
    database: Session = Depends(get_db),
):
    conversation = database.get(
        Conversation,
        conversation_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    database.delete(conversation)
    database.commit()
