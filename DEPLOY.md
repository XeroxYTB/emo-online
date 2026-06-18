# Déploiement Emo Online — GitHub Pages + API cloud

## Architecture

| Composant | Hébergement | URL |
|-----------|-------------|-----|
| **Frontend** (React) | GitHub Pages | https://xeroxytb.github.io/emo-online |
| **API** (FastAPI, LLM, Stripe, agent) | Fly.io (Docker) | https://emo-online-xeroxytb.fly.dev |
| **MongoDB** | MongoDB Atlas | cluster EmoCluster |

GitHub Pages ne peut pas exécuter Python/MongoDB — l’API tourne sur Fly.io (gratuit possible).

---

## 1. Activer GitHub Pages

1. Repo **Settings** → **Pages**
2. **Source** : **GitHub Actions**

---

## 2. Secrets GitHub (Settings → Secrets → Actions)

| Secret | Exemple |
|--------|---------|
| `FLY_API_TOKEN` | `fly auth token` (voir ci-dessous) |
| `MONGO_URL` | `mongodb+srv://user:pass@emocluster....mongodb.net/...` |
| `DB_NAME` | `emo` |
| `GOOGLE_CLIENT_ID` | Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | idem |
| `OPENAI_API_KEY` | au moins une clé LLM |
| `STRIPE_API_KEY` | sk_live_... ou test |
| `STRIPE_BASIC_LINK` | lien Payment Link Stripe |
| `EMO_ADMIN_EMAILS` | ton@email.com |

Optionnel : `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, liens Stripe premium/ultra.

---

## 3. Fly.io (backend API)

```bash
# Installer flyctl : https://fly.io/docs/hands-on/install-flyctl/
fly auth login
fly apps create emo-online-xeroxytb
fly auth token
# Copie le token → secret GitHub FLY_API_TOKEN
```

Atlas **Network Access** : autorise `0.0.0.0/0`.

---

## 4. Google OAuth

[Google Cloud Console](https://console.cloud.google.com/apis/credentials) :

- **Origines JavaScript autorisées** : `https://xeroxytb.github.io`
- **URI de redirection** : `https://emo-online-xeroxytb.fly.dev/api/auth/google/callback`

---

## 5. Déployer

Push sur `main` → workflow **Deploy** :

1. Build + déploie l’API Docker sur Fly.io (agents Go inclus)
2. Build le frontend avec `REACT_APP_BACKEND_URL=https://emo-online-xeroxytb.fly.dev`
3. Publie sur GitHub Pages

Ou manuel : **Actions** → **Deploy** → **Run workflow**.

---

## 6. Vérifier

- Site : https://xeroxytb.github.io/emo-online
- API : https://emo-online-xeroxytb.fly.dev/api/health
- Agent : panneau **Agent** → télécharger `Emo-Agent.exe`

---

## Alternative cloud (AWS / GCP / Azure)

Utilise `Dockerfile` (monolithe) ou `Dockerfile.fly` (API seule) sur Cloud Run, Container Apps ou App Runner. Variables :

```
EMO_SERVE_FRONTEND=false
EMO_PUBLIC_BACKEND_URL=https://TON-API
EMO_FRONTEND_URL=https://xeroxytb.github.io/emo-online
CORS_ORIGINS=https://xeroxytb.github.io
```

Puis mets à jour `REACT_APP_BACKEND_URL` dans `.github/workflows/deploy.yml`.

---

## Dev local

```cmd
cd /d "H:\Emo Online Final\emo\backend"
start.bat
```

Frontend : `cd emo/frontend && npm start` avec `.env` :
```
REACT_APP_BACKEND_URL=http://127.0.0.1:8010
```
