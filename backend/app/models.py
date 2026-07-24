"""
Pydantic schemas for API request/response bodies and MongoDB documents.

MongoDB document shape for a conversation (Phase 1 — no summarization yet,
that arrives in Phase 3):

{
    "_id": ObjectId,
    "session_id": "uuid-string",
    "messages": [
        {"role": "user" | "assistant", "content": str, "timestamp": datetime},
        ...
    ],
    "created_at": datetime,
    "updated_at": datetime,
}
"""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    message_count: int


class ConversationOut(BaseModel):
    session_id: str
    messages: list[Message]
    created_at: datetime
    updated_at: datetime
