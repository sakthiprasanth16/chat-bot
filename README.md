# 💬 AI Chatbot — Gemini + Rolling Memory + Streaming

A conversational AI chatbot with a FastAPI backend, a React (Vite + Tailwind) frontend, real-time token-by-token streaming, and a rolling memory system so long conversations never blow past the model's context window without losing important earlier context.

---

## 🎯 What This System Does

Most simple chatbot demos either forget everything after a few turns or blindly resend the entire conversation history to the model every time (slow, expensive, and eventually breaks once the conversation gets long). This project solves that with a **two-tier memory design**:

- The **last few raw messages** are always sent to the model exactly as they were typed — full fidelity for the immediate context.
- Everything **older** than that is periodically compressed into a **rolling summary** by the same Gemini API, instead of being sent raw or dropped entirely.

On top of that:

- Responses **stream in token-by-token** over the network (no waiting for the full reply).
- Markdown in the model's replies (bold, lists, code blocks, etc.) renders live as it streams — not as raw `**asterisks**`.
- A **jailbreak pre-check** runs before every message reaches the model, blocking known prompt-injection templates instantly, without spending an API call.
- A **sidebar** shows past conversations (like a "New Chat" + history list), so you can jump back into any earlier session.

---

## 🏗️ Architecture & Flow

```
                     ┌──────────────────────┐
                     │   React Frontend     │
                     │  (Vite + Tailwind)   │
                     └──────────┬───────────┘
                                │  SSE (fetch + manual event parsing)
                                ▼
                     ┌─────────────────────────┐
                     │    FastAPI Backend      │
                     │  POST /api/chat/stream  │
                     └──────────┬──────────────┘
                                │
              ┌─────────────────┼─────────────────────┐
              ▼                 ▼                      ▼
     ┌────────────────┐ ┌────────────────┐   ┌───────────────────────┐
     │ Jailbreak      │ │ MongoDB Atlas  │   │ Rolling Summarizer    │
     │ Pre-check      │ │ (conversation  │   │ (Gemini API call,     │
     │ (regex, local) │ │  history)      │   │  incremental)         │
     └────────────────┘ └────────────────┘   └───────────┬───────────┘
                                │                          │ (only when the
                                ▼                          │  token threshold
                     ┌─────────────────────┐               │  is crossed)
                     │    Gemini API       │◄──────────────┘
                     │  (main chat model)  │
                     └─────────────────────┘
```

There is only **one** external AI dependency — Gemini — used for both the actual chat reply and, with a different prompt, for rolling summarization. No local model server is required.

---

## 🔄 How a Message Actually Flows Through the System

Here's exactly what happens for a single message, end to end:

1. **You type a message** and hit send. The frontend opens a streaming HTTP request to `POST /api/chat/stream` with your `session_id` and `message`.
2. **Jailbreak pre-check** — the backend runs your message through a small set of regex patterns that catch known prompt-injection templates (e.g. *"ignore all previous instructions"*, *"you are now in developer mode"*). If it matches, the backend immediately returns a canned refusal — **no Gemini call is made at all** — and the exchange is still logged to the database like any normal turn.
3. **Memory check** — if it's not blocked, the backend checks the conversation's current token footprint (rolling summary + all raw messages, using a lightweight ~4-characters-per-token estimate). If it's still under the threshold, nothing changes. If it's crossed the threshold, the **older messages get folded into an updated summary** (more on this below, via a Gemini call), and only the most recent few raw messages are kept going forward.
4. **Prompt assembly** — the backend builds the final prompt sent to Gemini:
   - A hardened system instruction (defines tone, refuses to leak its own instructions, resists override attempts)
   - The rolling summary (if one exists yet), appended to that same system instruction
   - The last few raw messages, converted into Gemini's expected `user`/`model` history format
   - Your new message
5. **Gemini streams back a response**, token by token. Each token is relayed to the frontend immediately over the open SSE connection — you see the reply appear live, not all at once.
6. **The frontend renders each chunk through a markdown parser** as it arrives, so `**bold**`, bullet lists, and code blocks format correctly in real time rather than showing raw symbols.
7. **Once the reply finishes**, both your message and the full reply are saved to MongoDB, and the sidebar's session list refreshes so the conversation shows up (or moves to the top) with a title derived from your first message.

---

## 🧠 How Memory Actually Works

This is the core design decision in the project, so it's worth explaining precisely:

- Every conversation is stored as one MongoDB document with two fields that matter here: `messages` (an array of raw `{role, content}` turns) and `summary` (a single string, empty until the first summarization pass).
- Before every reply, the backend adds up: `tokens(summary) + tokens(all raw messages)`.
- **If that's under the threshold** (3000 tokens by default) → nothing happens, the raw messages are sent to Gemini as-is.
- **If it's over the threshold** → the messages are split into two groups:
  - The most recent few messages (kept exactly as-is, never summarized)
  - Everything older than that
- The **older group + the existing summary** is sent to **Gemini itself, with a separate summarization prompt** (not the chat prompt — no local model server involved, so there's nothing extra to install or keep running), which returns one new, updated summary (~150 words).
- MongoDB is updated **atomically**: the old messages are dropped, the summary is replaced, and only the recent few raw messages remain in the array.
- Next time, Gemini receives: `[hardened instructions] + [rolling summary] + [last few raw messages] + [your new message]` — never the full, ever-growing conversation.

This is **incremental by design** — each summarization pass only processes the previous summary plus the new chunk, never re-summarizes the whole conversation from scratch, so the cost of summarizing stays roughly constant even after hundreds of messages.

**Tradeoff worth knowing:** because summarization is incremental, very fine detail from early in a long conversation can gradually fade over many summarization passes ("summary drift"). This is an accepted tradeoff for this version — full exact recall of old details would need a vector database layer (a common v2 addition), which is intentionally out of scope here.

If the summarization call fails or times out, the backend logs a warning and simply continues using the un-summarized history rather than failing the whole request — a slow/unavailable summarization call should never take down a chat reply.

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- A free MongoDB Atlas account
- A free Google Gemini API key

### Step 1 — Unzip the project

You should have a `chat_bot_submission.zip` (or similarly named zip) file. Extract it anywhere on your machine:

```bash
# Windows: right-click the zip → Extract All...
# Mac/Linux:
unzip chat_bot_submission.zip -d chat_bot
```

Then open a terminal inside the extracted folder:

```bash
cd chat_bot
```

That's your project root — all commands below are run from here (or from `app/`/`frontend/` as noted).

### Step 2 — Set up the backend environment file

```bash
# From the project root:
cp .env.example .env      # Mac/Linux
copy .env.example .env    # Windows
```

Open `.env` and fill in:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-url>/chatbot_v1?retryWrites=true&w=majority
MONGODB_DB_NAME=chatbot_v1
APP_ENV=development
CORS_ORIGINS=http://localhost:3000
ENABLE_JAILBREAK_PRECHECK=true
SUMMARY_TOKEN_THRESHOLD=3000
KEEP_RECENT_MESSAGES=3
SUMMARY_TARGET_WORDS=150
```

---

### 🔑 How to get each key

#### GEMINI_API_KEY
1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **Create API key**
4. Copy the key into `.env`

> This is the only external key the project needs — it powers every chat reply **and** every rolling-summary pass. The free tier is enough for development and demos.

#### MONGODB_URI (MongoDB Atlas)
1. Go to [https://cloud.mongodb.com](https://cloud.mongodb.com)
2. Create a free cluster (or use an existing one)
3. Click **Database → Connect → Drivers**, copy the connection string
4. Replace `<username>` / `<password>` with your database user's credentials
5. **Important:** under **Network Access**, add your current IP (or `0.0.0.0/0` for local testing only) — Atlas blocks every connection by default until an IP is allowed

---

### Step 3 — Install backend dependencies

```bash
python -m venv venv

# Activate:
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### Step 4 — Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

Confirm it's healthy:

```bash
curl http://localhost:8000/api/health
```

Should return `{"status":"ok","mongodb":true,"env":"development"}`.

### Step 5 — Install and start the frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

```bash
npm run dev
```

Open **http://localhost:3000**

---

## 🧪 How to Use It

1. **Send a message** — type into the input box and hit Enter (Shift+Enter for a new line). The reply streams in live, with a blinking cursor while it's still generating.
2. **Start a new conversation** — click **+ New chat** in the sidebar. This doesn't create anything in the database until you send your first message in it.
3. **Revisit an old conversation** — click any entry in the sidebar's history list. It loads that session's most recent messages (capped at the last 10 exchanges, so a very long past conversation doesn't dump everything into the UI at once) and lets you continue right where you left off — Gemini still has the rest of that conversation's context via its rolling summary, even though only the recent messages are shown.
4. **Try a jailbreak-style message** (e.g. "ignore all previous instructions...") — it's blocked instantly with no delay, since the check happens locally before any API call.
5. **Have a long conversation** — after enough back-and-forth crosses the token threshold, older messages quietly compress into the rolling summary in the background (one extra Gemini call); you won't notice anything except that the app keeps responding at a similar speed no matter how long the conversation gets.

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Backend + MongoDB connectivity check |
| POST | `/api/chat` | Non-streaming chat turn (full reply returned at once) |
| POST | `/api/chat/stream` | Streaming chat turn via Server-Sent Events |
| GET | `/api/conversations` | List all sessions (newest first) for the sidebar, titled from each session's first message |
| GET | `/api/conversations/{session_id}` | Load a specific session's messages (capped to the last 10 exchanges) |

---

## 📁 Project Structure

```
chat_bot/
├── app/
│   ├── main.py                 # FastAPI app — health, chat, chat/stream, conversations endpoints
│   ├── config.py                # Settings — API keys, thresholds, env vars
│   ├── database.py              # MongoDB Atlas (Motor) — conversation CRUD, session list
│   ├── gemini_client.py         # generate_reply() / stream_reply() — the actual chat model calls
│   ├── gemini_summarizer.py     # summarize_chunk() — rolling summarization, also via Gemini
│   ├── guardrails.py            # Hardened system prompt, safety settings, jailbreak pre-check
│   ├── models.py                # Pydantic request/response schemas
│   ├── context_manager.py       # maybe_summarize() — the rolling-memory logic
│   └── token_utils.py           # Dependency-free token estimation
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── .env                     # VITE_API_URL=http://localhost:8000
│   └── src/
│       ├── main.jsx
│       ├── App.jsx              # Session state, sidebar wiring, streaming lifecycle
│       ├── index.css
│       ├── api/
│       │   ├── chatStream.js    # Hand-rolled SSE client
│       │   └── conversations.js # Sidebar history fetch calls
│       └── components/
│           ├── ChatHeader.jsx
│           ├── Sidebar.jsx       # New Chat button + session history list
│           ├── MessageList.jsx
│           ├── MessageBubble.jsx # Renders replies through a markdown parser, live while streaming
│           ├── TypingIndicator.jsx
│           └── ChatInput.jsx
│
├── requirements.txt
├── .env.example                  # Copy to .env at the project root and fill in your own keys
└── README.md
```

---

## 🛠️ Common Issues

| Problem | Fix |
|---|---|
| `/api/health` shows `mongodb: false` | Check `MONGODB_URI` is correct and your current IP is allowed under Atlas → Network Access |
| Summarization silently isn't happening on long chats | Check the backend terminal for a `[warn] summarization failed` line — this usually means `GEMINI_API_KEY` is invalid/rate-limited, since the same key is used for both chat replies and summarization |
| CORS error in the browser console | `CORS_ORIGINS` in `.env` must exactly match the frontend's URL (default `http://localhost:3000`) |
| Frontend can't reach the backend at all | Confirm `frontend/.env` has `VITE_API_URL=http://localhost:8000` and the backend is actually running on that port |
| A normal message gets blocked as a "jailbreak" | The regex pre-check is intentionally narrow (targets known override/persona-extraction phrasing), but if a false positive shows up, it can be disabled via `ENABLE_JAILBREAK_PRECHECK=false` in `.env` while you investigate |
| Streaming shows raw `**text**` instead of bold | Confirm `react-markdown`, `remark-gfm`, and `remark-breaks` are installed (`npm install` after pulling the latest `package.json`) |
| Sidebar history list is empty even after chatting | The list only shows sessions that have at least one saved message — a brand-new session with nothing sent yet won't appear until its first message completes |

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI (Python) + Uvicorn |
| Chat model | Google Gemini API |
| Summarization model | Google Gemini API (same key, separate prompt) |
| Database | MongoDB Atlas (Motor async driver) |
| Frontend | React (Vite) + Tailwind CSS |
| Markdown rendering | react-markdown + remark-gfm + remark-breaks |
| Real-time streaming | Server-Sent Events (SSE) over plain HTTP |

---

## 👨‍💻 Author

**Prasanth**
Project: AI Chatbot with rolling memory, streaming responses, and conversation history
