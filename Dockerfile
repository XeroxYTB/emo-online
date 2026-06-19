# Backend API — Hugging Face Spaces (Docker)
FROM golang:1.22-alpine AS agent-build
ARG EMO_AGENT_DEFAULT_BACKEND=https://xroxx-emo-online-api.hf.space
ENV EMO_AGENT_DEFAULT_BACKEND=${EMO_AGENT_DEFAULT_BACKEND}
WORKDIR /build/emo/agent-go
RUN apk add --no-cache bash
COPY emo/agent-go/ .
RUN chmod +x build.sh && ./build.sh

FROM python:3.11-slim
WORKDIR /emo

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libdbus-1-3 libxkbcommon0 libatspi2.0-0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

ENV PLAYWRIGHT_BROWSERS_PATH=/tmp/ms-playwright
RUN mkdir -p /tmp/ms-playwright && chmod -R 777 /tmp/ms-playwright

# HF Spaces: user non-root, seul /tmp est writable
ENV HF_HOME=/tmp/hf_cache
ENV XDG_CACHE_HOME=/tmp/hf_cache
RUN mkdir -p /tmp/hf_cache && chmod -R 777 /tmp/hf_cache

COPY emo/backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && playwright install chromium

COPY emo/backend ./backend
COPY --from=agent-build /build/emo/backend/agent_binaries ./backend/agent_binaries

WORKDIR /emo/backend
ENV EMO_SERVE_FRONTEND=false
ENV EMO_DEV_MODE=false
ENV PYTHONUNBUFFERED=1
ENV PORT=8010

EXPOSE 8010
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8010} --workers 1
