/**
 * Streams a chat turn from POST /api/chat/stream.
 *
 * The backend sends Server-Sent Events (`data: {...}\n\n`), same protocol
 * `test_sse_client.py` parses on the Python side. Browsers' built-in
 * EventSource only supports GET, so we use fetch()'s readable stream and
 * parse the SSE framing by hand — same approach as the Python client.
 *
 * Event shapes from the backend: {type: "typing"} | {type: "token", content}
 * | {type: "done", full_text, message_count} | {type: "error", detail}
 *
 * apiBase uses `??` (not `||`) so an intentionally-empty VITE_API_URL
 * (same-origin deploys, e.g. the HF Space build) is respected rather than
 * falling back to the localhost dev default — `"" || x` would wrongly
 * pick `x` since "" is falsy, but `"" ?? x` correctly keeps "".
 *
 * @param {object} params
 * @param {string} params.sessionId
 * @param {string} params.message
 * @param {(event: object) => void} params.onEvent - called for every event
 * @param {AbortSignal} [params.signal] - to cancel an in-flight stream
 */
export async function streamChat({ sessionId, message, onEvent, signal }) {
  const apiBase = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

  const response = await fetch(`${apiBase}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`Stream request failed: ${response.status} ${response.statusText}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by a blank line
    let boundary;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      const dataLine = rawEvent.split("\n").find((line) => line.startsWith("data: "));
      if (!dataLine) continue;

      let event;
      try {
        event = JSON.parse(dataLine.slice("data: ".length));
      } catch {
        continue; // skip malformed chunk rather than crashing the stream
      }

      onEvent(event);
      if (event.type === "done" || event.type === "error") return;
    }
  }
}
