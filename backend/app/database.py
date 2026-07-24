"""
MongoDB Atlas connection (via Motor, the async driver) and simple
persistence helpers for conversation history.

Phase 1 scope: store/retrieve the raw message list per session_id.
Phase 3 will extend the conversation document with a rolling `summary`
field and logic to trim `messages` once the token threshold is hit.
"""
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        _db = get_client()[settings.mongodb_db_name]
    return _db


async def ping() -> bool:
    """Used by the /health endpoint to confirm Atlas connectivity."""
    await get_client().admin.command("ping")
    return True


async def ensure_indexes() -> None:
    await get_db().conversations.create_index("session_id", unique=True)


async def get_conversation(session_id: str) -> dict | None:
    return await get_db().conversations.find_one({"session_id": session_id})


async def create_conversation(session_id: str) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "session_id": session_id,
        "messages": [],
        "summary": "",  # rolling summary, populated once token threshold is hit (Phase 3)
        "created_at": now,
        "updated_at": now,
    }
    await get_db().conversations.insert_one(doc)
    return doc


async def get_or_create_conversation(session_id: str) -> dict:
    convo = await get_conversation(session_id)
    if convo is None:
        convo = await create_conversation(session_id)
    return convo


async def append_messages(session_id: str, new_messages: list[dict]) -> None:
    """Push one or more message dicts and bump updated_at in one round trip."""
    await get_db().conversations.update_one(
        {"session_id": session_id},
        {
            "$push": {"messages": {"$each": new_messages}},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )


async def list_conversations(limit: int = 50) -> list[dict]:
    """
    Phase 6 — sidebar history list. Returns newest-first, and only pulls
    the *first* message of each conversation (via $slice) rather than the
    full messages array, since the sidebar only needs it to build a title
    preview. `_id` (Mongo's ObjectId) is excluded here since it isn't
    JSON-serializable and the route has no use for it.
    """
    cursor = (
        get_db()
        .conversations.find(
            {},
            {
                "_id": 0,
                "session_id": 1,
                "created_at": 1,
                "updated_at": 1,
                "messages": {"$slice": 1},
            },
        )
        .sort("updated_at", -1)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def replace_summary_and_trim(
    session_id: str, new_summary: str, kept_messages: list[dict]
) -> None:
    """
    Phase 3: after a rolling summarization pass, atomically swap in the
    new summary and drop the now-summarized older messages, keeping only
    `kept_messages` (the most recent N raw messages) in the array.
    """
    await get_db().conversations.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "summary": new_summary,
                "messages": kept_messages,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
