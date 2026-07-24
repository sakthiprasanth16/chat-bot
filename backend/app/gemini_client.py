"""
Thin wrapper around the Gemini API.

Phase 1: a single non-streaming `generate_reply()` call using the full
raw message history. Phase 2 will add a streaming variant for the
WebSocket endpoint. Phase 4 will harden SYSTEM_PROMPT and enable
safety_settings properly + add the local regex pre-check.
"""
import google.generativeai as genai

from app.config import settings
from app.guardrails import HARDENED_SYSTEM_PROMPT, get_gemini_safety_settings

genai.configure(api_key=settings.gemini_api_key)

# Phase 4: hardened prompt now lives in app/guardrails.py (single source of
# truth, shared with nothing else for now but keeps this file focused on
# the Gemini call itself rather than prompt text).
SYSTEM_PROMPT = HARDENED_SYSTEM_PROMPT


def _to_gemini_history(messages: list[dict]) -> list[dict]:
    """Convert our {role: 'user'|'assistant', content} messages into the
    {role: 'user'|'model', parts:[...]} shape the Gemini SDK expects."""
    history = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        history.append({"role": role, "parts": [m["content"]]})
    return history


def _build_system_instruction(summary: str) -> str:
    """
    Phase 3: fold the rolling summary (if any) into the system
    instruction rather than the chat history, so the history array can
    stay just the last few raw messages (kept exactly as Gemini expects
    alternating user/model turns), while the summary still gives Gemini
    the earlier context.
    """
    if not summary:
        return SYSTEM_PROMPT
    return (
        f"{SYSTEM_PROMPT}\n\n"
        "Summary of the earlier part of this conversation (may not "
        "include every detail — treat as helpful context, not ground truth):\n"
        f"{summary}"
    )


def generate_reply(
    history_messages: list[dict], new_user_message: str, summary: str = ""
) -> str:
    """
    Non-streaming call, used by the plain REST /api/chat endpoint.
    `history_messages` should already be the *trimmed* recent-message
    list (context_manager.maybe_summarize handles the trimming); `summary`
    is the rolling summary of everything older than that.
    """
    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=_build_system_instruction(summary),
        safety_settings=get_gemini_safety_settings(),
    )
    chat = model.start_chat(history=_to_gemini_history(history_messages))
    response = chat.send_message(new_user_message)
    return response.text


def stream_reply(history_messages: list[dict], new_user_message: str, summary: str = ""):
    """
    Streaming generator variant for the WebSocket endpoint. Same
    trimmed-history + summary contract as generate_reply() above.
    """
    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=_build_system_instruction(summary),
        safety_settings=get_gemini_safety_settings(),
    )
    chat = model.start_chat(history=_to_gemini_history(history_messages))
    response = chat.send_message(new_user_message, stream=True)
    for chunk in response:
        if chunk.text:
            yield chunk.text
