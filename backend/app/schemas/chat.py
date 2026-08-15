from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    prompt: str = Field(
        min_length=1,
        max_length=5000,
    )

    conversation_id: int | None = None


class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    source_type: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationSummaryResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse]

    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    conversation_id: int
    message: ChatMessageResponse
