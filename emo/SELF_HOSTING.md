# Émo — Self-hosting Guide

## What you have
Complete source code of Émo. Deploy on your own infrastructure to keep 100% of revenue.

## Stack
- **Backend** : Python 3.11 + FastAPI + MongoDB (Motor)
- **Frontend** : React 19 + Tailwind + Shadcn
- **Agent local** : Go (cross-compilé Win/macOS/Linux)
- **LLM** : Claude Sonnet 4.5 via Emergent LLM Key OR your own Anthropic key
- **Payments** : Stripe Checkout one-shot €20

## Quick deploy (Docker recommended)

### 1. Backend
```bash
cd backend
cp .env.example .env
# Edit .env :
#   MONGO_URL=mongodb://mongo:27017   (or your MongoDB Atlas URL)
#   DB_NAME=emo
#   EMERGENT_LLM_KEY=sk-emergent-xxx  (your key)
#   STRIPE_API_KEY=sk_live_xxx        (your Stripe production key)
#   EMO_ADMIN_EMAILS=you@your.domain
#   CORS_ORIGINS=https://your.domain

pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001
```

### 2. Frontend
```bash
cd frontend
cp .env.example .env
# Edit .env :
#   REACT_APP_BACKEND_URL=https://api.your.domain

yarn install
yarn build
# Serve /build/ via Nginx, Vercel, Netlify, Cloudflare Pages, etc.
```

### 3. Agent binaries (one-time)
```bash
cd agent-go
EMO_AGENT_DEFAULT_BACKEND=https://api.your.domain ./build.sh
# Binaires générés dans backend/agent_binaries/
```

### 4. MongoDB
- Use MongoDB Atlas (free tier OK) or self-host
- Backup the `licenses` and `users` collections regularly

## Deployment options
- **Vercel + Render** : Vercel for frontend, Render for backend+MongoDB (cheap)
- **Railway** : everything in one place, deploy from GitHub
- **DigitalOcean App Platform** : full stack, $12/month
- **VPS** (Hetzner, OVH) : your VPS + Caddy/Nginx reverse proxy, max control
- **Cloudflare Pages + Workers** : edge deployment

## Security checklist
- [ ] Change `STRIPE_API_KEY` to your live key (sk_live_...)
- [ ] Set `EMO_ADMIN_EMAILS` to YOUR email
- [ ] Set `CORS_ORIGINS` to your real domain (not `*`)
- [ ] Get your own `EMERGENT_LLM_KEY` from emergent.com OR switch to direct Anthropic API
- [ ] Backup MongoDB regularly
- [ ] Enable HTTPS (Caddy/Cloudflare/Vercel does it automatically)
- [ ] Configure Stripe webhook URL in Stripe Dashboard → Developers → Webhooks: `https://api.your.domain/api/webhook/stripe`

## How to make money
- Free tier: 10 messages/day (configurable in `server.py` — DAILY_MESSAGES constant)
- Lifetime: €20 one-shot via Stripe
- Funds → Stripe Dashboard → Payouts → your bank (auto 2-7 days)

## Customize
- **Persona** : `/app/backend/emo_prompts.py` — change Émo's identity, modes, tools
- **Pricing** : `LICENSE_PRICE_EUR` + `DAILY_MESSAGES` in `server.py`
- **Branding** : frontend `index.css` (colors), `Login.jsx` (logo), README.txt in agent bundle
- **Tools** : add new tools in `emo_prompts.py` (`EMO_TOOLS`) + execute_tool() in `server.py`

## Support
This is your code now. Fork it, modify it, ship it.
