# Déploiement Emo Online — GitHub Pages + Hugging Face Spaces

## Architecture

| Composant | Hébergement | URL |
|-----------|-------------|-----|
| **Frontend** (React) | GitHub Pages + domaine IONOS | **https://xeroxytb.com** |
| **API** (FastAPI, LLM, Stripe, agent) | Hugging Face Spaces (Docker) | https://xroxx-emo-online-api.hf.space |
| **MongoDB** | MongoDB Atlas | cluster EmoCluster |

**Gratuit, sans carte bancaire** (Fly.io et Koyeb demandent une carte).

---

## 1. Domaine custom IONOS → GitHub Pages

### DNS chez IONOS (domaine `xeroxytb.com`)

| Type | Nom / Host | Valeur |
|------|------------|--------|
| **A** | `@` | `185.199.108.153` |
| **A** | `@` | `185.199.109.153` |
| **A** | `@` | `185.199.110.153` |
| **A** | `@` | `185.199.111.153` |
| **CNAME** | `www` | `xeroxytb.github.io` |

*(Les 4 enregistrements A sont requis pour la racine `@` avec GitHub Pages.)*

### GitHub

1. Repo **emo-online** → **Settings** → **Pages**
2. **Custom domain** : `xeroxytb.com`
3. Coche **Enforce HTTPS** (après validation DNS, ~10 min à 24 h)
4. Le fichier `emo/frontend/public/CNAME` contient déjà `xeroxytb.com`

### Google OAuth (obligatoire après changement de domaine)

[Google Cloud Console](https://console.cloud.google.com/apis/credentials) → client OAuth :

- **Origines JS** : `https://xeroxytb.com`, `https://www.xeroxytb.com`
- **Redirect URI** (inchangé, côté API) : `https://xroxx-emo-online-api.hf.space/api/auth/google/callback`

---

## 2. GitHub Pages

Settings → **Pages** → Source = **GitHub Actions**

---

## 3. Créer le Space Hugging Face (1 fois)

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
| `EMO_PUBLIC_BACKEND_URL` | `https://xroxx-emo-online-api.hf.space` |
| `EMO_FRONTEND_URL` | `https://xeroxytb.com` |
| `CORS_ORIGINS` | `https://xeroxytb.com,https://www.xeroxytb.com,https://xeroxytb.github.io` |
| `GOOGLE_CLIENT_ID` | Google Console |
| `GOOGLE_CLIENT_SECRET` | idem |
| `OPENAI_API_KEY` | au moins une clé LLM |
| `ANTHROPIC_API_KEY` | optionnel |
| `GEMINI_API_KEY` | optionnel |
| `EMO_ADMIN_EMAILS` | ton email |

Atlas **Network Access** : autorise `0.0.0.0/0`.

---

## 5. Google OAuth

[Google Cloud Console](https://console.cloud.google.com/apis/credentials) :

- **Origines JS** : `https://xeroxytb.com`, `https://www.xeroxytb.com`
- **Redirect URI** : `https://xroxx-emo-online-api.hf.space/api/auth/google/callback`

---

## 6. Déployer

Push sur `main` → workflow **Deploy** :

1. Push le code vers le Space HF (si `HF_TOKEN` configuré)
2. HF rebuild le Docker automatiquement
3. Publie le frontend sur GitHub Pages

Test API : https://xroxx-emo-online-api.hf.space/api/health

**Important** : utilise l’URL `*.hf.space`, pas la page Hub (`huggingface.co/spaces/...`).

---

## Dev local

```cmd
cd emo\backend && start.bat
cd emo\frontend && npm start
```
