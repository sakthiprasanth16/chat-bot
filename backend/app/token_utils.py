"""
Approximate token counting — no external dependency, no network call.

We deliberately avoid tiktoken here: it needs to download its encoding
file from a remote blob URL on first use, which can fail in offline or
locked-down environments (and did, in testing). Since this count is only
used to trigger the rolling-summarization threshold -- a budget guardrail,
not a billing-accurate figure -- a simple characters-per-token heuristic
is good enough. The commonly cited rule of thumb for English text across
GPT/Gemini-family tokenizers is ~4 characters per token.
"""

_CHARS_PER_TOKEN = 4


def count_tokens(text: str) -> int:
    if not text:
        return 0
    # Slightly padded (ceil-ish) so we err on the side of summarizing a
    # little early rather than late.
    return max(1, (len(text) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN)


def count_messages_tokens(messages: list[dict]) -> int:
    return sum(count_tokens(m["content"]) for m in messages)
