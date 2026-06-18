# Emo Online

IA personnelle — **frontend** sur GitHub Pages, **API + agent** sur Fly.io (ou AWS/GCP/Azure).

- Site : https://xeroxytb.github.io/emo-online
- API : https://emo-online-xeroxytb.fly.dev
- Guide complet : [DEPLOY.md](DEPLOY.md)

## Déploiement rapide

1. **GitHub Pages** : Settings → Pages → Source = GitHub Actions
2. **Secrets** : `FLY_API_TOKEN`, `MONGO_URL`, `GOOGLE_CLIENT_*`, `OPENAI_API_KEY`, `STRIPE_*`
3. **Fly.io** : `fly apps create emo-online-xeroxytb`
4. Push sur `main` → workflow **Deploy**

## Dev local

```cmd
cd /d "H:\Emo Online Final\emo\backend"
start.bat
```

```cmd
cd /d "H:\Emo Online Final\emo\frontend"
npm install
echo REACT_APP_BACKEND_URL=http://127.0.0.1:8010> .env
npm start
```

## Structure

```
emo/backend/     FastAPI + MongoDB + LLM + Stripe + agent relay
emo/frontend/    React (GitHub Pages)
emo/agent-go/    Agent local (1 exe + permissions)
```

Voir [DEPLOY.md](DEPLOY.md) pour OAuth Google, Atlas, et alternatives cloud.
