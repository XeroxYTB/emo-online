# Déploiement Emo Online — GitHub Pages + Hugging Face Spaces

## Architecture

| Composant | Hébergement | URL |
|-----------|-------------|-----|
| **Frontend** (React) | GitHub Pages | https://xeroxytb.github.io/emo-online |
| **API** (FastAPI, LLM, Stripe, agent) | Hugging Face Spaces (Docker) | https://xeroxytb-emo-online-api.hf.space |
| **MongoDB** | MongoDB Atlas | cluster EmoCluster |

**Gratuit, sans carte bancaire** (Fly.io et Koyeb demandent une carte).

---

## 1. GitHub Pages

Settings → **Pages** → Source = **GitHub Actions**

---

## 2. Créer le Space Hugging Face (1 fois)

1. Compte gratuit : [huggingface.co/join](https://huggingface.co/join) (GitHub OK)
2. Crée un Space : [new-space?sdk=docker](https://huggingface.co/new-space?sdk=docker)
   - Owner : `XeroxYTB`
   - Name : `emo-online-api`
   - SDK : **Docker**
   - Visibility : **Public**
3. Token HF : [Settings → Access Tokens](https://huggingface.co/settings/tokens) (Write)
   - Secret GitHub : `HF_TOKEN`

---

## 3. Secrets du Space HF (Settings → Variables and secrets)

Dans le Space `emo-online-api` → **Settings** → **Variables and secrets** :

| Variable | Valeur |
|----------|--------|
| `MONGO_URL` | URI MongoDB Atlas |
| `DB_NAME` | `emo` |
| `EMO_PUBLIC_BACKEND_URL` | `https://xeroxytb-emo-online-api.hf.space` |
| `EMO_FRONTEND_URL` | `https://xeroxytb.github.io/emo-online` |
| `CORS_ORIGINS` | `https://xeroxytb.github.io` |
| `GOOGLE_CLIENT_ID` | Google Console |
| `GOOGLE_CLIENT_SECRET` | idem |
| `OPENAI_API_KEY` | au moins une clé LLM |
| `ANTHROPIC_API_KEY` | optionnel |
| `GEMINI_API_KEY` | optionnel |
| `EMO_ADMIN_EMAILS` | ton email |

Atlas **Network Access** : autorise `0.0.0.0/0`.

---

## 4. Google OAuth

[Google Cloud Console](https://console.cloud.google.com/apis/credentials) :

- **Origines JS** : `https://xeroxytb.github.io`
- **Redirect URI** : `https://xeroxytb-emo-online-api.hf.space/api/auth/google/callback`

---

## 5. Déployer

Push sur `main` → workflow **Deploy** :

1. Push le code vers le Space HF (si `HF_TOKEN` configuré)
2. HF rebuild le Docker automatiquement
3. Publie le frontend sur GitHub Pages

Test API : https://xeroxytb-emo-online-api.hf.space/api/health

**Important** : utilise l’URL `*.hf.space`, pas la page Hub (`huggingface.co/spaces/...`).

---

## Dev local

```cmd
cd emo\backend && start.bat
cd emo\frontend && npm start
```
