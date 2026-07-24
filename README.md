# Chatbot

FastAPI + MongoDB Atlas + Gemini chat app with rolling summarization
(also Gemini-backed — no local model server required). Deployed as a
single Docker web service on Render's free tier.

## Required environment variables (set in Render's dashboard)

| Name | Notes |
|---|---|
| `GEMINI_API_KEY` | required |
| `MONGODB_URI` | your MongoDB Atlas connection string |
| `MONGODB_DB_NAME` | optional, defaults to `chatbot_v1` |
| `GEMINI_MODEL` | optional, defaults to `gemini-3.1-flash-lite` |

MongoDB Atlas must allow inbound connections from `0.0.0.0/0` under
Network Access, since Render doesn't use a fixed outbound IP on the
free tier.

## Notes on this deploy

- Frontend (React/Vite) and backend (FastAPI) are served from the same
  container/origin — `app/main.py`'s static-file block at the bottom
  serves the built frontend, so no separate frontend hosting or CORS
  configuration is needed.
- Free tier sleeps after 15 minutes of inactivity; the next request
  wakes it back up (cold start, roughly 30-60s).
- Summarization now runs through the Gemini API (`app/gemini_summarizer.py`)
  instead of a local Ollama server — no extra infrastructure needed.
