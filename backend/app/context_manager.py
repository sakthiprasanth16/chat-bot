"""
Phase 3 — ties together token counting, Gemini-based summarization, and
MongoDB trimming into a single "check and summarize if needed" step,
called at the start of every turn (both REST and WebSocket).

Final prompt sent to Gemini = [rolling summary] + [last 2-3 raw
messages] + [new user query] — this module is what produces that
summary + trimmed-message pair; gemini_client.py assembles the final
prompt from them.
"""
import asyncio

from app import database
from app.config import settings
from app.gemini_summarizer import summarize_chunk
from app.token_utils import count_messages_tokens, count_tokens


async def maybe_summarize(session_id: str, convo: dict) -> dict:
    """
    Inspect the conversation's current token footprint (summary + raw
    messages). If it's under threshold, return convo unchanged. If over
    threshold, summarize the older portion via Gemini (previous summary +
    new chunk only — never the whole conversation from scratch), trim
    MongoDB down to the most recent `keep_recent_messages`, and return
    the updated convo dict.
    """
    messages = convo["messages"]
    summary = convo.get("summary", "")

    total_tokens = count_tokens(summary) + count_messages_tokens(messages)
    keep_n = settings.keep_recent_messages

    if total_tokens <= settings.summary_token_threshold or len(messages) <= keep_n:
        return convo

    older_chunk = messages[:-keep_n]
    recent_kept = messages[-keep_n:]

    # summarize_chunk() is a blocking call to the Gemini API — run it in a
    # worker thread so it doesn't block the event loop / other sessions.
    loop = asyncio.get_running_loop()
    new_summary = await loop.run_in_executor(None, summarize_chunk, summary, older_chunk)

    await database.replace_summary_and_trim(session_id, new_summary, recent_kept)

    convo = dict(convo)
    convo["summary"] = new_summary
    convo["messages"] = recent_kept
    return convo
