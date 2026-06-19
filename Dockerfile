# Hugging Face Spaces — API légère (gratuit, sans carte)
# Pas de build Go agent ni Playwright (trop lourd pour le tier free HF)
FROM python:3.11-slim
WORKDIR /emo

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV HF_HOME=/tmp/hf_cache
ENV XDG_CACHE_HOME=/tmp/hf_cache
RUN mkdir -p /tmp/hf_cache && chmod -R 777 /tmp/hf_cache

COPY emo/backend/requirements.render.txt ./backend/requirements.render.txt
RUN pip install --no-cache-dir -r backend/requirements.render.txt

COPY emo/backend ./backend

WORKDIR /emo/backend
ENV EMO_SERVE_FRONTEND=false
ENV EMO_DEV_MODE=false
ENV EMO_BROWSER_ENABLED=false
ENV PYTHONUNBUFFERED=1
ENV PORT=8010

EXPOSE 8010
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8010} --workers 1
