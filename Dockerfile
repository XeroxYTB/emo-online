# Backend API (frontend = GitHub Pages) — Koyeb / Docker
FROM golang:1.22-alpine AS agent-build
WORKDIR /build/emo/agent-go
RUN apk add --no-cache bash
COPY emo/agent-go/ .
RUN chmod +x build.sh && ./build.sh

FROM python:3.11-slim
WORKDIR /emo
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY emo/backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY emo/backend ./backend
COPY --from=agent-build /build/emo/backend/agent_binaries ./backend/agent_binaries
WORKDIR /emo/backend
ENV EMO_SERVE_FRONTEND=false
ENV EMO_DEV_MODE=false
ENV PYTHONUNBUFFERED=1
EXPOSE 8010
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8010}
