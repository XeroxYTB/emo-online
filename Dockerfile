# Emo Online — image production (API + frontend statique + binaires agent)
FROM golang:1.22-alpine AS agent-build
WORKDIR /build/emo/agent-go
RUN apk add --no-cache bash
COPY emo/agent-go/ .
RUN chmod +x build.sh && ./build.sh

FROM node:22-alpine AS frontend-build
WORKDIR /src/frontend
COPY emo/frontend/package.json emo/frontend/package-lock.json* emo/frontend/yarn.lock* ./
RUN npm install --legacy-peer-deps 2>/dev/null || npm install
COPY emo/frontend/ .
ARG REACT_APP_BACKEND_URL=
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
ENV CI=false
ENV DISABLE_ESLINT_PLUGIN=true
RUN npm run build

FROM python:3.11-slim
WORKDIR /emo
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY emo/backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY emo/backend ./backend
COPY --from=agent-build /build/emo/backend/agent_binaries ./backend/agent_binaries
COPY --from=frontend-build /src/frontend/build ./frontend/build
WORKDIR /emo/backend
ENV EMO_SERVE_FRONTEND=true
ENV EMO_DEV_MODE=false
ENV PYTHONUNBUFFERED=1
EXPOSE 8010
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8010}
