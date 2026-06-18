---
title: Emo Online API
emoji: 🧠
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 8010
pinned: false
---

# Emo Online

IA personnelle — **frontend** sur GitHub Pages, **API + agent** sur Hugging Face Spaces (gratuit, sans carte).

- Site : https://xeroxytb.github.io/emo-online
- API : https://xeroxytb-emo-online-api.hf.space
- Guide complet : [DEPLOY.md](DEPLOY.md)

## Déploiement rapide

1. **GitHub Pages** : Settings → Pages → Source = GitHub Actions
2. **Hugging Face Space** : [créer le Space Docker](https://huggingface.co/new-space?sdk=docker) lié au repo `emo-online`
3. **Secrets HF Space** : `MONGO_URL`, `GOOGLE_CLIENT_*`, clés LLM (Settings → Variables)
4. Push sur `main` → API rebuild HF + frontend GitHub Pages

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
Dockerfile       Image API pour Hugging Face Spaces
```
