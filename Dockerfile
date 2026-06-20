# Hugging Face — API + navigateur Playwright (Chromium headless interactif)
FROM python:3.11-slim
WORKDIR /emo

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 libx11-6 libxext6 \
    libxcb1 libdbus-1-3 libatspi2.0-0 libxshmfence1 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

ENV HF_HOME=/tmp/hf_cache
ENV XDG_CACHE_HOME=/tmp/hf_cache
RUN mkdir -p /tmp/hf_cache && chmod -R 777 /tmp/hf_cache

COPY emo/backend/requirements.render.txt ./backend/requirements.render.txt
RUN pip install --no-cache-dir -r backend/requirements.render.txt \
    && playwright install chromium

COPY emo/backend ./backend
COPY emo/agent ./agent
RUN mkdir -p ./backend/agent_binaries

WORKDIR /emo/backend
ENV EMO_SERVE_FRONTEND=false
ENV EMO_DEV_MODE=false
ENV EMO_BROWSER_ENABLED=true
ENV EMO_SKIP_STARTUP_PROBE=true
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

EXPOSE 7860
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
