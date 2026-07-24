# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build the React frontend (Vite)
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-build

WORKDIR /frontend

# VITE_API_URL="" means the built app calls relative paths like
# /api/chat/stream instead of an absolute host — required since frontend
# and backend are served from the same origin in this deployment.
ENV VITE_API_URL=""

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ ./
RUN npm run build
# Output lands in /frontend/dist

# ---------------------------------------------------------------------------
# Stage 2 — Python backend + the built frontend
# ---------------------------------------------------------------------------
FROM python:3.11-slim

RUN useradd -m -u 1000 appuser
ENV HOME=/home/appuser \
    PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY backend/ ./app_src/
# Backend code expects to be imported as the "app" package (see
# `from app import database` etc. in main.py/context_manager.py/...),
# so it lives at /app/app.
RUN mv /app/app_src /app/app

# Drop the built frontend where main.py's static mount expects it.
COPY --from=frontend-build /frontend/dist ./app/static

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

RUN chown -R appuser:appuser /app /home/appuser
USER appuser

# Render injects $PORT at runtime — start.sh reads it, this EXPOSE is
# documentation only (Render doesn't require a fixed port to be exposed).
EXPOSE 10000

ENTRYPOINT ["/app/start.sh"]
