# Déploiement Emo Online — GitHub Pages + Koyeb

## Architecture

| Composant | Hébergement | URL |
|-----------|-------------|-----|
| **Frontend** (React) | GitHub Pages | https://xeroxytb.github.io/emo-online |
| **API** (FastAPI, LLM, Stripe, agent) | Koyeb (Docker) | https://emo-online-api.koyeb.app |
| **MongoDB** | MongoDB Atlas | cluster EmoCluster |

GitHub Pages ne peut pas exécuter Python — l’API tourne sur **Koyeb** (gratuit, sans carte bancaire).

---

## 1. Activer GitHub Pages

1. Repo **Settings** → **Pages**
2. **Source** : **GitHub Actions**

---

## 2. Secrets GitHub (Settings → Secrets → Actions)

| Secret | Description |
|--------|-------------|
| `KOYEB_TOKEN` | Token API depuis [app.koyeb.com/settings/api](https://app.koyeb.com/settings/api) |
| `MONGO_URL` | URI MongoDB Atlas |
| `DB_NAME` | `emo` |
| `GOOGLE_CLIENT_ID` | Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | idem |
| `OPENAI_API_KEY` | au moins une clé LLM |
| `STRIPE_*` | optionnel |

Optionnel : `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, liens Stripe.

---

## 3. Koyeb (backend API)

1. Compte gratuit : [app.koyeb.com](https://app.koyeb.com) → **Continue with GitHub**
2. Installe l’app Koyeb sur le repo `emo-online`
3. **Settings → API** → crée un token → secret GitHub `KOYEB_TOKEN`
4. Atlas **Network Access** : autorise `0.0.0.0/0`

Premier déploiement : push sur `main` ou **Actions → Deploy → Run workflow**.

---

## 4. Google OAuth

[Google Cloud Console](https://console.cloud.google.com/apis/credentials) :

- **Origines JavaScript** : `https://xeroxytb.github.io`
- **URI de redirection** : `https://emo-online-api.koyeb.app/api/auth/google/callback`

---

## 5. Vérifier

- Site : https://xeroxytb.github.io/emo-online
- API : https://emo-online-api.koyeb.app/api/health
- Agent : panneau **Agent** → télécharger `Emo-Agent.exe`

---

## Déploiement manuel (local)

```bash
# Token Koyeb + secrets dans l'environnement, puis :
bash scripts/koyeb-deploy.sh
```
