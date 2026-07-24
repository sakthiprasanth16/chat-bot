"""
Entrypoint.

Endpoints:
    GET  /api/health              -> checks API + MongoDB Atlas connectivity
    POST /api/chat                -> non-streaming chat turn
    POST /api/chat/stream          -> streaming chat turn via Server-Sent Events

WebSocket streaming (Phase 2) was removed after repeated connection drops
on Windows (ProactorEventLoop + websockets library). Streaming is back via
plain HTTP SSE instead — no separate protocol/library, just a chunked
response over the same connection type everything else already uses.
"""
import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app import database
from app.config import settings
from app.context_manager import maybe_summarize
from app.gemini_client import generate_reply, stream_reply
from app.guardrails import check_jailbreak_attempt, JAILBREAK_REFUSAL_MESSAGE
from app.models import ChatRequest, ChatResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.ensure_indexes()
    yield


app = FastAPI(title="Chatbot API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    try:
        await database.ping()
        mongo_ok = True
    except Exception as exc:  # noqa: BLE001 - surfaced to caller for debugging
        mongo_ok = False
        return {"status": "degraded", "mongodb": mongo_ok, "error": str(exc)}
    return {"status": "ok", "mongodb": mongo_ok, "env": settings.app_env}


_TITLE_MAX_CHARS = 60
_HISTORY_MAX_PAIRS = 10  # last 10 user/assistant pairs = 20 messages


def _make_title(first_message_content: str) -> str:
    text = (first_message_content or "").strip()
    if not text:
        return "New chat"
    return text if len(text) <= _TITLE_MAX_CHARS else text[:_TITLE_MAX_CHARS].rstrip() + "…"


@app.get("/api/conversations")
async def list_conversations():
    """Sidebar history list — newest first, titled from each session's
    first message (truncated)."""
    docs = await database.list_conversations()
    out = []
    for d in docs:
        first_content = d["messages"][0]["content"] if d.get("messages") else ""
        out.append(
            {
                "session_id": d["session_id"],
                "title": _make_title(first_content),
                "created_at": d["created_at"],
                "updated_at": d["updated_at"],
            }
        )
    return out


@app.get("/api/conversations/{session_id}")
async def get_conversation_history(session_id: str):
    """Loads a session's messages when the user clicks it in the sidebar,
    capped to the most recent 10 pairs so old, very long sessions don't
    dump a huge payload into the UI at once."""
    convo = await database.get_conversation(session_id)
    if convo is None:
        raise HTTPException(status_code=404, detail="session not found")

    messages = convo["messages"]
    max_messages = _HISTORY_MAX_PAIRS * 2
    if len(messages) > max_messages:
        messages = messages[-max_messages:]

    return {
        "session_id": convo["session_id"],
        "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    convo = await database.get_or_create_conversation(payload.session_id)

    if settings.enable_jailbreak_precheck:
        check = check_jailbreak_attempt(payload.message)
        if check.blocked:
            # Store the turn like any normal message (complete/auditable
            # conversation log) but skip summarization and the Gemini call
            # entirely — no reason to spend either on a blocked message.
            await database.append_messages(
                payload.session_id,
                [
                    {"role": "user", "content": payload.message},
                    {"role": "assistant", "content": JAILBREAK_REFUSAL_MESSAGE},
                ],
            )
            updated = await database.get_conversation(payload.session_id)
            return ChatResponse(
                session_id=payload.session_id,
                reply=JAILBREAK_REFUSAL_MESSAGE,
                message_count=len(updated["messages"]),
            )

    try:
        convo = await maybe_summarize(payload.session_id, convo)
    except Exception as exc:  # noqa: BLE001
        # Same reasoning as websocket_handler.py: don't let a flaky
        # summarization call take down the whole chat turn.
        print(f"[warn] summarization failed for session={payload.session_id}: {exc}")

    try:
        reply_text = generate_reply(convo["messages"], payload.message, convo.get("summary", ""))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Gemini call failed: {exc}") from exc

    await database.append_messages(
        payload.session_id,
        [
            {"role": "user", "content": payload.message},
            {"role": "assistant", "content": reply_text},
        ],
    )

    updated = await database.get_conversation(payload.session_id)
    return ChatResponse(
        session_id=payload.session_id,
        reply=reply_text,
        message_count=len(updated["messages"]),
    )


def _sse_event(event_type: str, data: dict) -> str:
    """Formats one Server-Sent Events message. Each event is a single
    `data: <json>` line followed by a blank line — the blank line is what
    tells the client "this event is complete, deliver it now"."""
    payload = {"type": event_type, **data}
    return f"data: {json.dumps(payload)}\n\n"


async def _stream_chat_turn(payload: ChatRequest):
    """
    Async generator yielding SSE-formatted chunks. Mirrors the old
    websocket_handler.py event shape (typing / token / done / error) so a
    frontend written against that protocol only has to swap transport, not
    rewrite its event handling.
    """
    if not payload.message.strip():
        yield _sse_event("error", {"detail": "message cannot be empty"})
        return

    convo = await database.get_or_create_conversation(payload.session_id)

    if settings.enable_jailbreak_precheck:
        check = check_jailbreak_attempt(payload.message)
        if check.blocked:
            yield _sse_event("typing", {})
            yield _sse_event("token", {"content": JAILBREAK_REFUSAL_MESSAGE})
            await database.append_messages(
                payload.session_id,
                [
                    {"role": "user", "content": payload.message},
                    {"role": "assistant", "content": JAILBREAK_REFUSAL_MESSAGE},
                ],
            )
            updated = await database.get_conversation(payload.session_id)
            yield _sse_event(
                "done",
                {"full_text": JAILBREAK_REFUSAL_MESSAGE, "message_count": len(updated["messages"])},
            )
            return

    try:
        convo = await maybe_summarize(payload.session_id, convo)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] summarization failed for session={payload.session_id}: {exc}")

    history = convo["messages"]
    summary = convo.get("summary", "")

    yield _sse_event("typing", {})

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    _STREAM_END = object()

    def producer() -> None:
        try:
            for chunk in stream_reply(history, payload.message, summary):
                loop.call_soon_threadsafe(queue.put_nowait, ("token", chunk))
        except Exception as exc:  # noqa: BLE001 - relay any Gemini/SDK error to the client
            loop.call_soon_threadsafe(queue.put_nowait, ("error", str(exc)))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, _STREAM_END)

    producer_future = loop.run_in_executor(None, producer)

    full_text = ""
    errored = False
    while True:
        item = await queue.get()
        if item is _STREAM_END:
            break
        kind, data = item
        if kind == "token":
            full_text += data
            yield _sse_event("token", {"content": data})
        elif kind == "error":
            errored = True
            yield _sse_event("error", {"detail": data})

    await producer_future

    if errored:
        return

    await database.append_messages(
        payload.session_id,
        [
            {"role": "user", "content": payload.message},
            {"role": "assistant", "content": full_text},
        ],
    )
    updated = await database.get_conversation(payload.session_id)
    yield _sse_event("done", {"full_text": full_text, "message_count": len(updated["messages"])})


@app.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest):
    """
    Streaming counterpart to /api/chat. Plain HTTP + chunked transfer
    (Server-Sent Events), consumable with httpx's client.stream(), the
    browser's EventSource/fetch, or any HTTP client that reads the body
    incrementally — no websockets dependency.
    """
    return StreamingResponse(
        _stream_chat_turn(payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
# ---------------------------------------------------------------------------
# Serve the built React frontend (Docker deploy only).
#
# MUST be the last thing in this file — FastAPI matches routes in
# registration order, and the catch-all below would otherwise shadow every
# /api/* route defined above it.
#
# In local dev (`npm run dev` + `uvicorn` separately) app/static won't
# exist, so this block is a no-op and CORS handles cross-origin calls
# instead — nothing here breaks the existing dev workflow.
# ---------------------------------------------------------------------------
import os

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "static")

if os.path.isdir(_FRONTEND_DIST):
    _ASSETS_DIR = os.path.join(_FRONTEND_DIST, "assets")
    if os.path.isdir(_ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """SPA fallback: serve the matching static file if it exists,
        otherwise index.html so React Router-style client-side routes
        (if any are added later) still resolve correctly."""
        candidate = os.path.join(_FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))
