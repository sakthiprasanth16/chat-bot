// Sidebar data fetching — separate from chatStream.js since these are
// plain request/response calls, not SSE streams.
//
// BASE_URL falls back to "" (same-origin, relative paths) when
// VITE_API_URL isn't set — this is what makes it work once frontend and
// backend are served from the same Space/origin.
const BASE_URL = import.meta.env.VITE_API_URL || "";

export async function fetchConversations() {
  const res = await fetch(`${BASE_URL}/api/conversations`);
  if (!res.ok) throw new Error("Failed to load conversation list");
  return res.json();
}

export async function fetchConversationMessages(sessionId) {
  const res = await fetch(`${BASE_URL}/api/conversations/${sessionId}`);
  if (!res.ok) throw new Error("Failed to load conversation history");
  return res.json();
}
