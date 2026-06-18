# Emo Online



IA personnelle avec chat, mémoire, outils web et **agent local** (un seul exécutable par OS). Le site héberge LLM, auth, paiements ; l'agent ne gère que les permissions et l'exécution sur ton PC.



## Structure



```

emo/

  backend/          FastAPI + MongoDB + LLM + Stripe + relay agent

  frontend/         React (chat, panneau Agent à droite / mobile)

  agent-go/         Agent Go — binaire unique + interface permissions locale

  backend/agent_binaries/   Binaires compilés (CI / Docker)

```



## Déploiement en ligne (recommandé)



### 1. MongoDB Atlas



1. Crée un cluster gratuit sur [MongoDB Atlas](https://www.mongodb.com/atlas)

2. Copie l'URI `mongodb+srv://...`

3. Autorise l'accès réseau (`0.0.0.0/0` pour Render)



### 2. GitHub + Render



1. Push ce repo sur **GitHub** (`main`)

2. [Render](https://render.com) → **New Blueprint** → connecte le repo (`render.yaml`)

3. Renseigne les variables secrètes (voir `emo/backend/.env.example`)

4. **Google OAuth** : redirect URI = `https://TON-APP.onrender.com/api/auth/google/callback`

5. `EMO_PUBLIC_BACKEND_URL` et `EMO_FRONTEND_URL` = URL Render (même domaine)



Le Dockerfile compile le frontend, les binaires agent Go, et sert tout sur un seul port.



### 3. Variables obligatoires



| Variable | Exemple |

|----------|---------|

| `MONGO_URL` | `mongodb+srv://...` |

| `DB_NAME` | `emo` |

| `EMO_PUBLIC_BACKEND_URL` | `https://emo.onrender.com` |

| `EMO_FRONTEND_URL` | `https://emo.onrender.com` |

| `CORS_ORIGINS` | `https://emo.onrender.com` |

| `OPENAI_API_KEY` ou autre LLM | clé API |

| `STRIPE_*` | clés Stripe si paiements activés |



### 4. Agent local (Windows / macOS / Linux)



1. Connecte-toi sur le site → panneau **Agent** (menu droit, ou icône engrenage sur mobile)

2. Choisis ta plateforme → **Télécharger Emo Agent**

3. Un **seul fichier** (`Emo-Agent.exe` ou `Emo-Agent`) contient déjà ton token et l'URL du site

4. Double-clique (Windows) ou `chmod +x Emo-Agent && ./Emo-Agent` (macOS/Linux)

5. L'interface locale (navigateur, port 17841) permet de régler les permissions puis démarrer l'agent



Plateformes : Windows x64, macOS Intel/ARM, Linux x64/ARM64.



## Dev local



```bash

# Backend

cd emo/backend

python -m venv .venv

.venv\Scripts\pip install -r requirements.txt   # Windows

cp .env.example .env   # éditer MONGO_URL

uvicorn server:app --reload --port 8010



# Frontend (autre terminal)

cd emo/frontend

npm install

echo REACT_APP_BACKEND_URL=http://127.0.0.1:8010 > .env

npm start



# Agent (nécessite Go 1.22+)

cd emo/agent-go

./build.sh

# puis lancer backend/agent_binaries/emo-agent-windows-amd64.exe (Windows)

```



MongoDB local : `mongodb://127.0.0.1:27017` ou Atlas.



## Docker local



```bash

docker build -t emo-online .

docker run -p 8010:8010 --env-file emo/backend/.env emo-online

```



## CI



GitHub Actions (`.github/workflows/ci.yml`) : import backend, build agent multi-OS, build frontend, build Docker.



## Sécurité



- Ne jamais committer `.env` ni tokens agent

- Roter les clés si elles ont été exposées

- L'agent exécute des commandes selon tes permissions locales — garde le token privé

