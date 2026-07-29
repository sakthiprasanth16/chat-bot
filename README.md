💬 AI Chatbot – Gemini + Rolling Memory + Streaming

A production-ready AI chatbot built with FastAPI, React (Vite + Tailwind CSS), Google Gemini, MongoDB Atlas, and Ollama. The application supports real-time streaming responses, rolling memory summarization, conversation history, markdown rendering, and jailbreak protection, enabling long-running conversations without exceeding the LLM context window.

✨ Key Features

- 🚀 Real-time token-by-token streaming responses (SSE)
- 🧠 Rolling memory using Ollama for long conversations
- 🤖 Google Gemini as the primary LLM
- 💾 MongoDB Atlas for conversation storage
- 📜 Live Markdown rendering
- 🛡️ Jailbreak and prompt injection pre-check
- 📂 Conversation history with sidebar navigation
- ⚡ FastAPI backend with React (Vite + Tailwind CSS) frontend
- ☁️ Deployable on Render

🛠️ Tech Stack

- Backend: FastAPI, Python, Uvicorn
- Frontend: React, Vite, Tailwind CSS
- LLM: Google Gemini API
- Memory Summarization: Ollama (Llama 3.2 1B)
- Database: MongoDB Atlas
- Streaming: Server-Sent Events (SSE)

This project demonstrates how to build a scalable conversational AI system that maintains context across long conversations while keeping API costs and context usage efficient.