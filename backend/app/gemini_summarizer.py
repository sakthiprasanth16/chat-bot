"""
app/gemini_summarizer.py

Replaces ollama_client.py — same job (rolling summarization), same
function contract (summarize_chunk(previous_summary, new_messages) ->
str), just backed by the Gemini API instead of a local Ollama server.
This removes the app's only non-Gemini/non-Mongo external dependency,
which is what makes it deployable on hosts that don't give you a shell
to install and run a background model server (Render free tier, etc.).

Incremental by design, same as the old client: every call summarizes
(previous_summary + new_chunk) only, never the whole conversation from
scratch, so each call stays small and roughly constant-cost regardless
of how long the overall conversation gets.
"""
import google.generativeai as genai

from app.config import settings

genai.configure(api_key=settings.gemini_api_key)

SUMMARY_PROMPT_TEMPLATE = """You are maintaining a running summary of an ongoing conversation.

Previous summary of the conversation so far:
{previous_summary}

New conversation messages to fold into the summary:
{new_chunk}

Write an updated summary that combines the previous summary with the new
messages above. Keep it to approximately {target_words} words. Preserve
concrete facts, names, numbers, preferences, and decisions. Do not
mention that you are an AI or that this is a summary — just write the
summary content directly, with no preamble."""


def _format_chunk(messages: list[dict]) -> str:
    return "\n".join(f"{m['role']}: {m['content']}" for m in messages)


def summarize_chunk(previous_summary: str, new_messages: list[dict]) -> str:
    """
    Blocking call to the Gemini API. Called from a worker thread by
    context_manager.py (via run_in_executor) so it doesn't block the
    async event loop — same reasoning as when this was a blocking httpx
    call to a local Ollama server.
    """
    prompt = SUMMARY_PROMPT_TEMPLATE.format(
        previous_summary=previous_summary.strip() or "(no summary yet — this is the first pass)",
        new_chunk=_format_chunk(new_messages),
        target_words=settings.summary_target_words,
    )

    model = genai.GenerativeModel(model_name=settings.gemini_model)
    response = model.generate_content(prompt)
    return response.text.strip()
