#!/usr/bin/env bash
# Deploy Emo API on Koyeb (free tier, no credit card)
set -euo pipefail

APP_NAME="${KOYEB_APP_NAME:-emo-online-api}"
GITHUB_REPO="${KOYEB_GITHUB_REPO:-github.com/XeroxYTB/emo-online}"
FRONTEND_URL="${EMO_FRONTEND_URL:-https://xeroxytb.github.io/emo-online}"
BACKEND_URL="${EMO_PUBLIC_BACKEND_URL:-https://${APP_NAME}.koyeb.app}"

if [ -z "${KOYEB_TOKEN:-}" ]; then
  echo "::warning::KOYEB_TOKEN absent — crée un token sur app.koyeb.com/settings/api puis ajoute-le dans GitHub Secrets"
  exit 0
fi

if [ -z "${MONGO_URL:-}" ]; then
  echo "::warning::MONGO_URL absent"
  exit 0
fi

export KOYEB_TOKEN

curl -fsSL https://raw.githubusercontent.com/koyeb/koyeb-cli/master/install.sh | bash
koyeb version

ENV_ARGS=(
  "PORT=8010"
  "DB_NAME=${DB_NAME:-emo}"
  "MONGO_URL=${MONGO_URL}"
  "EMO_PUBLIC_BACKEND_URL=${BACKEND_URL}"
  "EMO_FRONTEND_URL=${FRONTEND_URL}"
  "CORS_ORIGINS=https://xeroxytb.github.io"
  "GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID:-}"
  "GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET:-}"
  "OPENAI_API_KEY=${OPENAI_API_KEY:-}"
  "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}"
  "GEMINI_API_KEY=${GEMINI_API_KEY:-}"
  "GROQ_API_KEY=${GROQ_API_KEY:-}"
  "STRIPE_API_KEY=${STRIPE_API_KEY:-}"
  "STRIPE_BASIC_LINK=${STRIPE_BASIC_LINK:-}"
  "STRIPE_PREMIUM_LINK=${STRIPE_PREMIUM_LINK:-}"
  "STRIPE_ULTRA_LINK=${STRIPE_ULTRA_LINK:-}"
  "EMO_ADMIN_EMAILS=${EMO_ADMIN_EMAILS:-}"
)

if koyeb service get "${APP_NAME}" >/dev/null 2>&1; then
  echo "Service ${APP_NAME} exists — update env + redeploy"
  UPDATE_ARGS=()
  for kv in "${ENV_ARGS[@]}"; do
    UPDATE_ARGS+=(--env "$kv")
  done
  koyeb service update "${APP_NAME}" "${UPDATE_ARGS[@]}"
  koyeb service redeploy "${APP_NAME}" --use-cache
else
  echo "Creating Koyeb app + service ${APP_NAME}"
  INIT_ARGS=(
    app init "${APP_NAME}"
    --git "${GITHUB_REPO}"
    --git-branch main
    --git-builder docker
    --type WEB
    --instance-type nano
    --ports "8010:http"
    --routes "/:8010"
  )
  for kv in "${ENV_ARGS[@]}"; do
    INIT_ARGS+=(--env "$kv")
  done
  koyeb "${INIT_ARGS[@]}"
fi

echo "Backend URL: ${BACKEND_URL}"
echo "Health: ${BACKEND_URL}/api/health"
