# Emo Online

IA personnelle — **frontend** sur GitHub Pages, **API + agent** sur Koyeb.

- Site : https://xeroxytb.github.io/emo-online
- API : https://emo-online-api.koyeb.app
- Guide complet : [DEPLOY.md](DEPLOY.md)

## Déploiement rapide

1. **GitHub Pages** : Settings → Pages → Source = GitHub Actions
2. **Secrets** : `KOYEB_TOKEN`, `MONGO_URL`, `GOOGLE_CLIENT_*`, `OPENAI_API_KEY`, `STRIPE_*`
3. **Koyeb** : compte gratuit + token API
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
emo/agent-go/    Agent local (Windows/macOS/Linux)
Dockerfile       Image API pour Koyeb
scripts/         koyeb-deploy.sh
```
